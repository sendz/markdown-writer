"""Live Markdown auto-formatting while typing.

How it hooks in
---------------
The office does not instantiate extension code at start-up, so the global
document watcher is installed lazily the first time one of the extension's
commands runs (``Dispatch``) and, as a best effort, from the ``Job`` component
if the office chooses to run it.  Once installed, the watcher listens to the
``GlobalEventBroadcaster`` and installs an ``XModifyListener`` on every Writer
document that is created or loaded.  That listener reformats the paragraph the
cursor is in as Markdown is typed, Typora style: the markers are consumed and
replaced by real formatting.

The text transformation logic is deliberately plain Python (see
``mdwriter.markdown``) so it can be unit tested without a running office.
"""

import os

import uno
import unohelper

from com.sun.star.document import XDocumentEventListener
from com.sun.star.task import XJob
from com.sun.star.lang import XServiceInfo
from com.sun.star.util import XModifyListener

from mdwriter import formatter
from mdwriter.markdown import (
    HEADING_RE,
    BULLET_RE,
    NUMBER_RE,
    QUOTE_RE,
    FENCE_RE,
    split_inline,
)

# Numbering styles used for live lists.
BULLET_STYLE = "List 1"
NUMBER_STYLE = "Numbering 123"

DEBUG_LOG = os.environ.get("MARKDOWN_WRITER_DEBUG_LOG")


def _log(message):
    if not DEBUG_LOG:
        return
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------- #
# Live reformatting of the paragraph under the cursor
# ---------------------------------------------------------------------- #
def reformat(ctx, model):
    """Reformat the paragraph at the cursor. Returns True if anything changed.

    Everything is done with text cursors and paragraph properties.  The view
    cursor and ``.uno:`` dispatches are deliberately avoided: editing the
    document from inside a modify notification while the view is updating can
    crash the office.
    """
    if not formatter.is_writer(model):
        return False
    if model.getCurrentController() is None:
        return False

    text = model.getText()
    paragraph = _paragraph_cursor(model)
    content = paragraph.getString()
    if not content:
        return False
    _log("reformat content=%r" % (content,))

    # --- block markers ------------------------------------------------ #
    match = HEADING_RE.match(content)
    if match:
        _log("  heading %d: delete %d chars" % (
            len(match.group(1)), len(match.group(0)) - len(match.group(2))))
        _delete_prefix(text, paragraph, len(match.group(0)) - len(match.group(2)))
        _log("  set ParaStyleName=Heading %d" % len(match.group(1)))
        _set_paragraph_style(model, "Heading %d" % len(match.group(1)))
        return True

    if FENCE_RE.match(content.strip()):
        _log("  fence: clear + preformatted")
        _clear_paragraph(text, paragraph)
        _set_paragraph_style(model, formatter.CODE_BLOCK_STYLE)
        return True

    match = QUOTE_RE.match(content)
    if match:
        _log("  quote: delete prefix")
        _delete_prefix(text, paragraph, len(content) - len(match.group(1)))
        _set_paragraph_style(model, formatter.QUOTE_STYLE)
        return True

    match = BULLET_RE.match(content)
    if match:
        _log("  bullet: delete prefix + %s" % BULLET_STYLE)
        _delete_prefix(text, paragraph, len(content) - len(match.group(1)))
        _set_paragraph_numbering(model, BULLET_STYLE)
        return True

    match = NUMBER_RE.match(content)
    if match:
        _log("  number: delete prefix + %s" % NUMBER_STYLE)
        _delete_prefix(text, paragraph, len(content) - len(match.group(1)))
        _set_paragraph_numbering(model, NUMBER_STYLE)
        return True

    # --- inline markers ----------------------------------------------- #
    plain, spans = split_inline(content)
    if not spans or plain == content:
        return False

    _log("  inline: %r -> %r" % (content, plain))
    paragraph.setString(plain)
    _apply_spans(text, _paragraph_cursor(model), spans)
    return True


def _view_cursor(model):
    return model.getCurrentController().getViewCursor()


def _paragraph_cursor(model):
    text = model.getText()
    cursor = text.createTextCursorByRange(_view_cursor(model))
    cursor.gotoStartOfParagraph(False)
    cursor.gotoEndOfParagraph(True)
    return cursor


def _delete_prefix(text, paragraph, count):
    if count <= 0:
        return
    cursor = text.createTextCursorByRange(paragraph.getStart())
    cursor.goRight(count, True)
    cursor.setString("")


def _clear_paragraph(text, paragraph):
    cursor = text.createTextCursorByRange(paragraph.getStart())
    cursor.gotoEndOfParagraph(True)
    cursor.setString("")


def _set_paragraph_style(model, style):
    _paragraph_cursor(model).setPropertyValue("ParaStyleName", style)


def _set_paragraph_numbering(model, style):
    _paragraph_cursor(model).setPropertyValue("NumberingStyleName", style)


def _apply_spans(text, paragraph, spans):
    cursor = text.createTextCursorByRange(paragraph.getStart())
    for start, end, kind, payload in spans:
        cursor.gotoStartOfParagraph(False)
        cursor.goRight(start, False)
        cursor.goRight(end - start, True)
        _apply_span(cursor, kind, payload)


def _apply_span(cursor, kind, payload):
    if kind == "bold":
        cursor.setPropertyValue("CharWeight", formatter.BOLD_WEIGHT)
    elif kind == "italic":
        cursor.setPropertyValue(
            "CharPosture", uno.Enum("com.sun.star.awt.FontSlant", "ITALIC"))
    elif kind == "code":
        cursor.setPropertyValue("CharStyleName", formatter.CHAR_CODE_STYLE)
    elif kind == "strike":
        try:
            cursor.setPropertyValue(
                "CharStrikeout",
                uno.Enum("com.sun.star.awt.FontStrikeout", "SINGLE"))
        except Exception:
            pass
    elif kind == "link":
        cursor.setPropertyValue("HyperLinkURL", payload)
        cursor.setPropertyValue("CharStyleName", "Internet link")


# ---------------------------------------------------------------------- #
# Status bar indicator (Live mode)
# ---------------------------------------------------------------------- #
_indicator = None


def _current_frame(ctx):
    try:
        desktop = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)
        return desktop.getCurrentFrame()
    except Exception:
        return None


def refresh_indicator(ctx):
    """Show or hide the status bar indicator reflecting Live mode."""
    global _indicator
    frame = _current_frame(ctx)
    if frame is None:
        return
    try:
        if LIVE_ENABLED:
            if _indicator is None:
                _indicator = frame.createStatusIndicator()
                _indicator.start("Markdown: Live", 100)
        else:
            if _indicator is not None:
                _indicator.end()
                _indicator = None
    except Exception as exc:
        _log("status indicator failed: %r" % (exc,))
        _indicator = None


# ---------------------------------------------------------------------- #
# Per-document listener
# ---------------------------------------------------------------------- #
LIVE_ENABLED = True

_attached = {}
_busy = False
_internal = set()


def mark_internal(model):
    """Exclude *model* from live formatting (e.g. the preview document)."""
    _internal.add(model)
    detach(model)


def attach(ctx, model):
    """Install the live listener on *model* (idempotent)."""
    if not LIVE_ENABLED or not formatter.is_writer(model):
        return
    if model in _internal or model in _attached:
        return
    listener = LiveListener(ctx, model)
    model.addModifyListener(listener)
    _attached[model] = listener
    _log("attached live listener to %r" % (model,))
    refresh_indicator(ctx)


def detach(model):
    listener = _attached.pop(model, None)
    if listener is not None:
        try:
            model.removeModifyListener(listener)
        except Exception:
            pass


class LiveListener(unohelper.Base, XModifyListener):

    def __init__(self, ctx, model):
        self.ctx = ctx
        self.model = model

    def modified(self, event):
        global _busy
        if _busy or not LIVE_ENABLED:
            return
        _busy = True
        try:
            reformat(self.ctx, self.model)
        except Exception as exc:
            _log("reformat error: %r" % (exc,))
        finally:
            _busy = False

    def disposing(self, source):
        _attached.pop(self.model, None)


# ---------------------------------------------------------------------- #
# Global document event watcher
# ---------------------------------------------------------------------- #
class DocumentWatcher(unohelper.Base, XDocumentEventListener):

    def __init__(self, ctx):
        self.ctx = ctx

    def documentEventOccured(self, event):
        name = event.EventName
        source = event.Source
        if name in ("OnNew", "OnLoad", "OnViewCreated", "OnDocumentOpened"):
            attach(self.ctx, source)
        elif name in ("OnUnload", "OnViewClosed"):
            detach(source)

    def disposing(self, source):
        pass


_broadcaster = None


def bootstrap(ctx):
    """Register the global document watcher. Safe to call repeatedly."""
    global _broadcaster
    if _broadcaster is not None:
        return True
    try:
        watcher = DocumentWatcher(ctx)
        _broadcaster = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.GlobalEventBroadcaster", ctx)
        if hasattr(_broadcaster, "addDocumentEventListener"):
            _broadcaster.addDocumentEventListener(watcher)
        else:
            _broadcaster.addEventListener(watcher)
        _log("bootstrap: global document watcher registered")
        return True
    except Exception as exc:
        _log("bootstrap failed: %r" % (exc,))
        _broadcaster = None
        return False


# ---------------------------------------------------------------------- #
# Optional job (best effort automatic start-up hook)
# ---------------------------------------------------------------------- #
JOB_IMPLE_NAME = "com.sendyyeah.mdwriter.Job"
JOB_SERVICE_NAMES = ("com.sun.star.task.Job",)


def _find_document(value):
    try:
        if value.supportsService("com.sun.star.text.TextDocument"):
            return value
    except Exception:
        pass
    inner = getattr(value, "Value", None)
    if inner is not None and inner is not value:
        found = _find_document(inner)
        if found is not None:
            return found
    try:
        items = list(value)
    except TypeError:
        return None
    for item in items:
        found = _find_document(item)
        if found is not None:
            return found
    return None


class Job(unohelper.Base, XJob, XServiceInfo):

    def __init__(self, ctx, *args):
        self.ctx = ctx

    def getImplementationName(self):
        return JOB_IMPLE_NAME

    def supportsService(self, name):
        return name in JOB_SERVICE_NAMES

    def getSupportedServiceNames(self):
        return JOB_SERVICE_NAMES

    def execute(self, args):
        _log("Job.execute")
        bootstrap(self.ctx)
        model = _find_document(args)
        if model is not None:
            attach(self.ctx, model)
        return None
