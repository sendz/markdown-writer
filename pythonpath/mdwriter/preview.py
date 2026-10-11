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

from com.sun.star.awt import XActionListener, XTextListener, XFocusListener
from com.sun.star.beans import PropertyValue

from mdwriter import exporter
from mdwriter import md2html
from mdwriter import live

HTML_FILTER = "HTML (StarWriter)"

PUSHBUTTON_STANDARD = 0
POS_SIZE = 15  # X | Y | WIDTH | HEIGHT

# Default dialog size in real pixels (scaled to the display DPI at runtime).
DIALOG_PX_W, DIALOG_PX_H = 940, 600

PREVIEW_HTML = os.path.join(tempfile.gettempdir(), "mdwriter-preview.html")

_editors = []
_editor_busy = False
_scale = None


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


class _FocusListener(unohelper.Base, XFocusListener):

    def __init__(self, callback):
        self.callback = callback

    def focusGained(self, event):
        pass

    def focusLost(self, event):
        self.callback()

    def disposing(self, source):
        pass


# ---------------------------------------------------------------------- #
# Single-window editor
# ---------------------------------------------------------------------- #
def _screen_size(ctx, frame):
    try:
        win = frame.getContainerWindow()
        rect = win.getPosSize()
        return rect.Width, rect.Height
    except Exception:
        return 1280, 800


def edit_source(ctx, model, frame):
    """Open the source editor with a live preview beside it.

    LibreOffice has no supported way to embed a rendered document view inside a
    custom dialog (XContainerWindowProvider returns no window for a dialog
    peer), so the preview lives in its own read-only window that is positioned
    next to the editor and refreshed as you type.
    """
    md_path = os.path.join(tempfile.gettempdir(), "mdwriter-source.md")
    markdown_text = document_to_markdown(model, md_path)

    screen_w, screen_h = _screen_size(ctx, frame)
    editor_w = min(700, max(420, screen_w // 2))

    _write_html(markdown_text)
    dialog, control = _build_source_dialog(ctx, frame, markdown_text,
                                           width_px=editor_w, height_px=screen_h)
    preview_model = _open_preview(ctx)
    try:
        preview = preview_model.getCurrentController().getFrame().getContainerWindow()
        preview.setPosSize(editor_w, 0, max(200, screen_w - editor_w), screen_h, POS_SIZE)
    except Exception as exc:
        _log("preview positioning failed: %r" % (exc,))
    _load_preview(preview_model)

    def on_text_changed():
        # Only regenerate the HTML file here.  Modifying a document while the
        # dialog is processing key events can crash the office, so the preview
        # document is updated when focus leaves the field or on Refresh.
        try:
            _write_html(control.getText())
        except Exception as exc:
            _log("html write failed: %r" % (exc,))

    def refresh():
        _write_html(control.getText())
        _load_preview(preview_model)

    def on_focus_lost(event):
        _load_preview(preview_model)

    def apply():
        _apply_source(ctx, model, control.getText())

    def close():
        _close_editor(dialog, preview_model)

    control.addTextListener(_TextListener(on_text_changed))
    control.addFocusListener(_FocusListener(on_focus_lost))
    dialog.getControl("preview").addActionListener(_ActionListener(refresh))
    dialog.getControl("apply").addActionListener(_ActionListener(apply))
    dialog.getControl("close").addActionListener(_ActionListener(close))

    _editors.append((dialog, preview_model))
    dialog.setVisible(True)


def _open_preview(ctx):
    path = markdown_to_html_file("")
    doc = _desktop(ctx).loadComponentFromURL(
        uno.systemPathToFileUrl(path), "_blank", 0,
        (_prop("FilterName", HTML_FILTER),))
    # The preview must never be reformatted by live mode.
    live.mark_internal(doc)
    return doc


def _write_html(markdown_text):
    return markdown_to_html_file(markdown_text)


def _load_preview(preview_model):
    """Render the current PREVIEW_HTML file into the preview document."""
    global _editor_busy
    if _editor_busy:
        return
    _editor_busy = True
    try:
        text = preview_model.getText()
        cursor = text.createTextCursor()
        cursor.gotoStart(False)
        cursor.gotoEnd(True)
        cursor.setString("")
        cursor.gotoStart(False)
        cursor.insertDocumentFromURL(
            uno.systemPathToFileUrl(PREVIEW_HTML),
            (_prop("FilterName", HTML_FILTER),))
        preview_model.setModified(False)
    finally:
        _editor_busy = False


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


def _ui_scale(ctx, frame):
    """Pixels per dialog-model unit (the model unit depends on the display DPI)."""
    global _scale
    if _scale is not None:
        return _scale
    smgr = ctx.ServiceManager
    try:
        probe_model = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel", ctx)
        probe_model.setPropertyValue("Width", 100)
        probe_model.setPropertyValue("Height", 100)
        probe = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog", ctx)
        probe.setModel(probe_model)
        toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
        parent = frame.getContainerWindow() if frame is not None else None
        probe.createPeer(toolkit, parent)
        size = probe.getPeer().getPosSize()
        probe.dispose()
        _scale = (size.Width / 100.0, size.Height / 100.0)
    except Exception as exc:
        _log("scale probe failed: %r" % (exc,))
        _scale = (1.0, 1.0)
    return _scale


def _build_source_dialog(ctx, frame, markdown_text,
                         width_px=DIALOG_PX_W, height_px=DIALOG_PX_H):
    """Create the editor dialog. Returns (dialog, source_control)."""
    smgr = ctx.ServiceManager
    sx, sy = _ui_scale(ctx, frame)

    def mx(px):
        return int(round(px / sx))

    def my(px):
        return int(round(px / sy))

    margin = 6
    btn_h = 26
    btn_y = height_px - margin - btn_h
    model_dialog = smgr.createInstanceWithContext(
        "com.sun.star.awt.UnoControlDialogModel", ctx)
    model_dialog.setPropertyValue("Title", "Markdown Editor")
    model_dialog.setPropertyValue("Width", mx(width_px))
    model_dialog.setPropertyValue("Height", my(height_px))
    model_dialog.setPropertyValue("PositionX", mx(4))
    model_dialog.setPropertyValue("PositionY", my(4))

    edit = model_dialog.createInstance("com.sun.star.awt.UnoControlEditModel")
    _set(edit, Name="source", PositionX=mx(margin), PositionY=my(margin),
         Width=mx(width_px - 2 * margin), Height=my(btn_y - 2 * margin),
         MultiLine=True, VScroll=True, HScroll=True, Tabstop=True)
    model_dialog.insertByName("source", edit)

    preview_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(preview_btn, Name="preview", Label="Refresh Preview",
         PositionX=mx(margin), PositionY=my(btn_y),
         Width=mx(130), Height=my(btn_h), PushButtonType=PUSHBUTTON_STANDARD)
    model_dialog.insertByName("preview", preview_btn)

    ok_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(ok_btn, Name="apply", Label="Apply to Document",
         PositionX=mx(margin + 140), PositionY=my(btn_y),
         Width=mx(150), Height=my(btn_h), PushButtonType=PUSHBUTTON_STANDARD)
    model_dialog.insertByName("apply", ok_btn)

    close_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(close_btn, Name="close", Label="Close",
         PositionX=mx(margin + 300), PositionY=my(btn_y),
         Width=mx(70), Height=my(btn_h), PushButtonType=PUSHBUTTON_STANDARD)
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
