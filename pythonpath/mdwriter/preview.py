"""Markdown preview and source editing.

Two entry points:

* :func:`preview` renders the current document as Markdown, converts it to HTML
  and opens the result in a separate window (the "result" side).
* :func:`edit_source` opens a dialog with the document's raw Markdown for
  editing, with buttons to preview it and to apply it back (the "source" side).
"""

import os
import tempfile

import uno
import unohelper

from com.sun.star.awt import XActionListener
from com.sun.star.beans import PropertyValue

from mdwriter import exporter
from mdwriter import md2html

HTML_FILTER = "HTML (StarWriter)"

# com.sun.star.awt.PushButtonType
PUSHBUTTON_STANDARD = 0
PUSHBUTTON_OK = 1
PUSHBUTTON_CANCEL = 2

# XDialog.execute() results
DIALOG_OK = 1

PREVIEW_HTML = os.path.join(tempfile.gettempdir(), "mdwriter-preview.html")


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
# Source editor dialog
# ---------------------------------------------------------------------- #
class _ActionListener(unohelper.Base, XActionListener):

    def __init__(self, callback):
        self.callback = callback

    def actionPerformed(self, event):
        self.callback()

    def disposing(self, source):
        pass


def edit_source(ctx, model, frame):
    """Open a dialog to edit the document's Markdown source."""
    md_path = os.path.join(tempfile.gettempdir(), "mdwriter-source.md")
    markdown_text = document_to_markdown(model, md_path)

    smgr = ctx.ServiceManager
    model_dialog = smgr.createInstanceWithContext(
        "com.sun.star.awt.UnoControlDialogModel", ctx)
    model_dialog.setPropertyValue("Title", "Markdown Source")
    model_dialog.setPropertyValue("Width", 400)
    model_dialog.setPropertyValue("Height", 300)
    model_dialog.setPropertyValue("PositionX", 120)
    model_dialog.setPropertyValue("PositionY", 80)

    edit = model_dialog.createInstance("com.sun.star.awt.UnoControlEditModel")
    _set(edit, Name="source", PositionX=8, PositionY=8, Width=384, Height=250,
         MultiLine=True, VScroll=True, HScroll=True, Tabstop=True)
    model_dialog.insertByName("source", edit)

    preview_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(preview_btn, Name="preview", Label="Preview", PositionX=8, PositionY=266,
         Width=80, Height=20, PushButtonType=PUSHBUTTON_STANDARD)
    model_dialog.insertByName("preview", preview_btn)

    ok_btn = model_dialog.createInstance("com.sun.star.awt.UnoControlButtonModel")
    _set(ok_btn, Name="apply", Label="Apply to Document", PositionX=232, PositionY=266,
         Width=160, Height=20, PushButtonType=PUSHBUTTON_OK)
    model_dialog.insertByName("apply", ok_btn)

    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model_dialog)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    parent = frame.getContainerWindow() if frame is not None else None
    dialog.createPeer(toolkit, parent)

    control = dialog.getControl("source")
    control.setText(markdown_text)

    def do_preview():
        markdown_to_html_file(control.getText())
        _desktop(ctx).loadComponentFromURL(
            uno.systemPathToFileUrl(PREVIEW_HTML), "_blank", 0,
            (_prop("FilterName", HTML_FILTER),))

    dialog.getControl("preview").addActionListener(_ActionListener(do_preview))

    try:
        if dialog.execute() == DIALOG_OK:
            _apply_source(ctx, model, control.getText())
    finally:
        dialog.dispose()


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
