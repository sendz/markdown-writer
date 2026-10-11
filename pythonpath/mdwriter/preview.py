"""Markdown preview and the Markdown source editor.

* :func:`preview` renders the current document as Markdown, converts it to HTML
  and opens the result in a separate window.
* :func:`edit_source` opens a modeless dialog with the document's Markdown
  source; **Apply to Document** renders it back into the current document.
"""

import os
import tempfile

import uno
import unohelper

from com.sun.star.awt import (
    XActionListener,
    XTextListener,
    XFocusListener,
    XTopWindowListener,
)
from com.sun.star.beans import PropertyValue

from mdwriter import exporter
from mdwriter import md2html

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


class _TopWindowListener(unohelper.Base, XTopWindowListener):

    def __init__(self, callback):
        self.callback = callback

    def windowOpened(self, event):
        pass

    def windowClosing(self, event):
        # Fired by the dialog's (X) button.
        self.callback()

    def windowClosed(self, event):
        pass

    def windowMinimized(self, event):
        pass

    def windowNormalized(self, event):
        pass

    def windowActivated(self, event):
        pass

    def windowDeactivated(self, event):
        pass

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
    """Open the Markdown source editor (a modeless dialog).

    There is no separate preview window: edit the Markdown and click
    *Apply to Document*, which renders it into the current document.
    """
    md_path = os.path.join(tempfile.gettempdir(), "mdwriter-source.md")
    markdown_text = document_to_markdown(model, md_path)

    screen_w, screen_h = _screen_size(ctx, frame)
    editor_w = min(700, max(420, screen_w // 2))
    editor_h = min(600, max(320, screen_h - 80))

    dialog, control = _build_source_dialog(ctx, frame, markdown_text,
                                           width_px=editor_w, height_px=editor_h)

    def apply():
        _apply_source(ctx, model, control.getText())

    def close():
        _close_editor(dialog)

    dialog.getControl("apply").addActionListener(_ActionListener(apply))
    dialog.getControl("close").addActionListener(_ActionListener(close))
    dialog.addTopWindowListener(_TopWindowListener(close))

    _editors.append(dialog)
    dialog.setVisible(True)


def _close_editor(dialog):
    try:
        dialog.dispose()
    except Exception:
        pass
    if dialog in _editors:
        _editors.remove(dialog)


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

    apply_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(apply_btn, Name="apply", Label="Apply to Document",
         PositionX=mx(margin), PositionY=my(btn_y),
         Width=mx(160), Height=my(btn_h), PushButtonType=PUSHBUTTON_STANDARD)
    model_dialog.insertByName("apply", apply_btn)

    close_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(close_btn, Name="close", Label="Close",
         PositionX=mx(margin + 170), PositionY=my(btn_y),
         Width=mx(90), Height=my(btn_h), PushButtonType=PUSHBUTTON_STANDARD)
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
