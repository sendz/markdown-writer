"""Markdown preview and a two-pane editor embedded in a single dialog.

* :func:`preview` renders the current document as Markdown, converts it to HTML
  and opens the result in a separate window.
* :func:`edit_source` opens a **single dialog** containing the Markdown source
  on the left and an embedded, live-updating document view on the right.  The
  embedded view is created by loading a document with ``ParentWindow`` set to
  the dialog's window peer, then positioning its window.
"""

import os
import tempfile

import uno
import unohelper

from com.sun.star.awt import XActionListener, XTextListener
from com.sun.star.beans import PropertyValue

from mdwriter import exporter
from mdwriter import md2html

HTML_FILTER = "HTML (StarWriter)"

PUSHBUTTON_STANDARD = 0

# dialog geometry (in 1/100 mm)
DIALOG_W, DIALOG_H = 944, 560
SRC_X, SRC_Y, SRC_W, SRC_H = 8, 8, 452, 500
EXP_X, EXP_Y, EXP_W, EXP_H = 468, 8, 468, 500
BTN_Y = 514
POS_SIZE = 15  # X | Y | WIDTH | HEIGHT

PREVIEW_HTML = os.path.join(tempfile.gettempdir(), "mdwriter-preview.html")

_editors = []
_editor_busy = False


def _log(message):
    path = os.environ.get("MARKDOWN_WRITER_DEBUG_LOG")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except Exception:
        pass


def _prop(name, value):
    prop = PropertyValue()
    prop.Name = name
    prop.Value = value
    return prop


def _desktop(ctx):
    return ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)


# ---------------------------------------------------------------------- #
# Rendering helpers (testable)
# ---------------------------------------------------------------------- #
def document_to_markdown(model, path):
    exporter.export_markdown(model, uno.systemPathToFileUrl(path))
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def markdown_to_html_file(markdown_text, path=PREVIEW_HTML):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(md2html.html_document(markdown_text))
    return path


def preview(ctx, model, path=None):
    """Render *model* as HTML and open it in its own window."""
    md_path = os.path.join(tempfile.gettempdir(), "mdwriter-preview.md")
    markdown_text = document_to_markdown(model, md_path)
    html_path = markdown_to_html_file(markdown_text, path or PREVIEW_HTML)
    _desktop(ctx).loadComponentFromURL(
        uno.systemPathToFileUrl(html_path), "_blank", 0,
        (_prop("FilterName", HTML_FILTER),))


# ---------------------------------------------------------------------- #
# Listeners
# ---------------------------------------------------------------------- #
class _ActionListener(unohelper.Base, XActionListener):

    def __init__(self, callback):
        self.callback = callback

    def actionPerformed(self, event):
        self.callback()

    def disposing(self, source):
        pass


class _TextListener(unohelper.Base, XTextListener):

    def __init__(self, callback):
        self.callback = callback

    def textChanged(self, event):
        self.callback()

    def disposing(self, source):
        pass


# ---------------------------------------------------------------------- #
# Single-window editor
# ---------------------------------------------------------------------- #
def edit_source(ctx, model, frame):
    """Open the source editor with the preview embedded in the same dialog."""
    md_path = os.path.join(tempfile.gettempdir(), "mdwriter-source.md")
    markdown_text = document_to_markdown(model, md_path)

    dialog, control = _build_source_dialog(ctx, frame, markdown_text)
    preview_model, preview_window = _embed_preview(ctx, dialog)
    _update_embedded(ctx, preview_model, markdown_text)

    def on_text_changed():
        global _editor_busy
        if _editor_busy:
            return
        _editor_busy = True
        try:
            _update_embedded(ctx, preview_model, control.getText())
        except Exception as exc:
            _log("live preview failed: %r" % (exc,))
        finally:
            _editor_busy = False

    def refresh():
        _update_embedded(ctx, preview_model, control.getText())

    def apply():
        _apply_source(ctx, model, control.getText())

    def close():
        _close_editor(dialog, preview_model)

    control.addTextListener(_TextListener(on_text_changed))
    dialog.getControl("preview").addActionListener(_ActionListener(refresh))
    dialog.getControl("apply").addActionListener(_ActionListener(apply))
    dialog.getControl("close").addActionListener(_ActionListener(close))

    _editors.append((dialog, preview_model))
    dialog.setVisible(True)


def _embed_preview(ctx, dialog):
    """Load an empty HTML document as a child window of *dialog*."""
    path = markdown_to_html_file("")
    doc = _desktop(ctx).loadComponentFromURL(
        uno.systemPathToFileUrl(path), "_blank", 0,
        (_prop("ParentWindow", dialog.getPeer()),))
    window = doc.getCurrentController().getFrame().getContainerWindow()
    window.setPosSize(EXP_X, EXP_Y, EXP_W, EXP_H, POS_SIZE)
    return doc, window


def _update_embedded(ctx, preview_model, markdown_text):
    path = markdown_to_html_file(markdown_text)
    text = preview_model.getText()
    cursor = text.createTextCursor()
    cursor.gotoStart(False)
    cursor.gotoEnd(True)
    cursor.setString("")
    cursor.gotoStart(False)
    cursor.insertDocumentFromURL(
        uno.systemPathToFileUrl(path),
        (_prop("FilterName", HTML_FILTER),))
    preview_model.setModified(False)


def _close_editor(dialog, preview_model):
    try:
        dialog.dispose()
    except Exception:
        pass
    try:
        preview_model.setModified(False)
        preview_model.close(False)
    except Exception:
        pass
    for entry in list(_editors):
        if entry[0] is dialog or entry[1] is preview_model:
            _editors.remove(entry)


def _build_source_dialog(ctx, frame, markdown_text):
    """Create the editor dialog. Returns (dialog, source_control)."""
    smgr = ctx.ServiceManager
    model_dialog = smgr.createInstanceWithContext(
        "com.sun.star.awt.UnoControlDialogModel", ctx)
    model_dialog.setPropertyValue("Title", "Markdown Editor")
    model_dialog.setPropertyValue("Width", DIALOG_W)
    model_dialog.setPropertyValue("Height", DIALOG_H)
    model_dialog.setPropertyValue("PositionX", 80)
    model_dialog.setPropertyValue("PositionY", 60)

    edit = model_dialog.createInstance("com.sun.star.awt.UnoControlEditModel")
    _set(edit, Name="source", PositionX=SRC_X, PositionY=SRC_Y,
         Width=SRC_W, Height=SRC_H, MultiLine=True, VScroll=True, HScroll=True,
         Tabstop=True)
    model_dialog.insertByName("source", edit)

    preview_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(preview_btn, Name="preview", Label="Refresh Preview", PositionX=SRC_X,
         PositionY=BTN_Y, Width=130, Height=24, PushButtonType=PUSHBUTTON_STANDARD)
    model_dialog.insertByName("preview", preview_btn)

    ok_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(ok_btn, Name="apply", Label="Apply to Document", PositionX=250,
         PositionY=BTN_Y, Width=150, Height=24, PushButtonType=PUSHBUTTON_STANDARD)
    model_dialog.insertByName("apply", ok_btn)

    close_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(close_btn, Name="close", Label="Close", PositionX=408,
         PositionY=BTN_Y, Width=52, Height=24, PushButtonType=PUSHBUTTON_STANDARD)
    model_dialog.insertByName("close", close_btn)

    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model_dialog)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    parent = frame.getContainerWindow() if frame is not None else None
    dialog.createPeer(toolkit, parent)

    control = dialog.getControl("source")
    control.setText(markdown_text)
    return dialog, control


def _apply_source(ctx, model, markdown_text):
    """Replace the document content with *markdown_text* rendered as text."""
    md_path = os.path.join(tempfile.gettempdir(), "mdwriter-apply.md")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(markdown_text)
    text = model.getText()
    cursor = text.createTextCursor()
    cursor.gotoStart(False)
    cursor.gotoEnd(True)
    cursor.setString("")
    cursor.gotoStart(False)
    cursor.insertDocumentFromURL(
        uno.systemPathToFileUrl(md_path),
        (_prop("FilterName", exporter.MARKDOWN_FILTER),))


def _set(control_model, **props):
    for name, value in props.items():
        control_model.setPropertyValue(name, value)
