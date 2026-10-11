"""Markdown preview and a two-pane (source + live preview) editor.

* :func:`preview` renders the current document as Markdown, converts it to HTML
  and opens the result in a separate window.
* :func:`edit_source` opens a **modeless** editor dialog: while you type in the
  source pane, a preview window is refreshed automatically, so source and
  result can sit side by side.
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

# com.sun.star.awt.PushButtonType (short values)
PUSHBUTTON_STANDARD = 0
PUSHBUTTON_OK = 1

PREVIEW_HTML = os.path.join(tempfile.gettempdir(), "mdwriter-preview.html")

# Keep modeless dialogs and their preview windows alive.
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
    """Render *model* as HTML and open it in a new window."""
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
# Source editor dialog (modeless) + live preview
# ---------------------------------------------------------------------- #
def edit_source(ctx, model, frame):
    """Open the source editor with a live-updating preview window."""
    md_path = os.path.join(tempfile.gettempdir(), "mdwriter-source.md")
    markdown_text = document_to_markdown(model, md_path)

    preview_model = _open_preview(ctx)
    dialog, control = _build_source_dialog(ctx, frame, markdown_text)
    _update_preview(ctx, preview_model, markdown_text)

    def on_text_changed():
        global _editor_busy
        if _editor_busy:
            return
        _editor_busy = True
        try:
            _update_preview(ctx, preview_model, control.getText())
        except Exception as exc:
            _log("live preview failed: %r" % (exc,))
        finally:
            _editor_busy = False

    def do_apply():
        _apply_source(ctx, model, control.getText())

    def do_close():
        _close_editor(dialog, preview_model)

    control.addTextListener(_TextListener(on_text_changed))
    dialog.getControl("preview").addActionListener(
        _ActionListener(lambda: _update_preview(ctx, preview_model, control.getText())))
    dialog.getControl("apply").addActionListener(_ActionListener(do_apply))
    dialog.getControl("close").addActionListener(_ActionListener(do_close))

    _editors.append((dialog, preview_model))
    dialog.setVisible(True)


def _open_preview(ctx):
    path = markdown_to_html_file("")
    return _desktop(ctx).loadComponentFromURL(
        uno.systemPathToFileUrl(path), "_blank", 0,
        (_prop("FilterName", HTML_FILTER),))


def _update_preview(ctx, preview_model, markdown_text):
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
    """Create the source editor dialog. Returns (dialog, source_control)."""
    smgr = ctx.ServiceManager
    model_dialog = smgr.createInstanceWithContext(
        "com.sun.star.awt.UnoControlDialogModel", ctx)
    model_dialog.setPropertyValue("Title", "Markdown Editor")
    model_dialog.setPropertyValue("Width", 420)
    model_dialog.setPropertyValue("Height", 320)
    model_dialog.setPropertyValue("PositionX", 120)
    model_dialog.setPropertyValue("PositionY", 80)

    edit = model_dialog.createInstance("com.sun.star.awt.UnoControlEditModel")
    _set(edit, Name="source", PositionX=8, PositionY=8, Width=404, Height=270,
         MultiLine=True, VScroll=True, HScroll=True, Tabstop=True)
    model_dialog.insertByName("source", edit)

    preview_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(preview_btn, Name="preview", Label="Refresh Preview", PositionX=8,
         PositionY=286, Width=120, Height=22, PushButtonType=PUSHBUTTON_STANDARD)
    model_dialog.insertByName("preview", preview_btn)

    ok_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(ok_btn, Name="apply", Label="Apply to Document", PositionX=232,
         PositionY=286, Width=140, Height=22, PushButtonType=PUSHBUTTON_STANDARD)
    model_dialog.insertByName("apply", ok_btn)

    close_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(close_btn, Name="close", Label="Close", PositionX=376,
         PositionY=286, Width=40, Height=22, PushButtonType=PUSHBUTTON_STANDARD)
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
