"""Markdown import/export helpers.

LibreOffice ships a built-in Markdown filter (``generic_Markdown``, filter name
``Markdown``), so importing and exporting is mostly a matter of opening/saving
with the right filter name.  These functions add menus and sensible defaults
around it.
"""

import uno

from com.sun.star.beans import PropertyValue

MARKDOWN_FILTER = "Markdown"

# ExecutableDialogResults.OK
DIALOG_OK = 1
# com.sun.star.ui.dialogs.TemplateDescription.{FILEOPEN_SIMPLE,FILESAVE_AUTOEXTENSION}
FILEOPEN_SIMPLE = 0
FILESAVE_AUTOEXTENSION = 2

MARKDOWN_EXTENSIONS = "*.md;*.markdown;*.mdown;*.mkd"


def prop(name, value):
    prop = PropertyValue()
    prop.Name = name
    prop.Value = value
    return prop


def _desktop(ctx):
    return ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)


# ---------------------------------------------------------------------- #
# Non-interactive building blocks (testable)
# ---------------------------------------------------------------------- #
def load_markdown(ctx, url):
    """Open a Markdown file as a Writer document."""
    props = (
        prop("FilterName", MARKDOWN_FILTER),
        prop("AsTemplate", False),
    )
    return _desktop(ctx).loadComponentFromURL(url, "_blank", 0, props)


def export_markdown(model, url):
    """Write *model* to *url* using the Markdown filter (document untouched)."""
    model.storeToURL(url, (prop("FilterName", MARKDOWN_FILTER),))


# ---------------------------------------------------------------------- #
# File pickers
# ---------------------------------------------------------------------- #
def _picker(ctx, template, filter_name, filter_pattern, default_name=""):
    picker = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.ui.dialogs.OfficeFilePicker", ctx)
    try:
        picker.initialize((template,))
    except Exception:
        pass
    picker.appendFilter(filter_name, filter_pattern)
    picker.setCurrentFilter(filter_name)
    if default_name:
        picker.setDefaultName(default_name)
    return picker


def choose_open_markdown(ctx):
    picker = _picker(ctx, FILEOPEN_SIMPLE, "Markdown", MARKDOWN_EXTENSIONS)
    if picker.execute() != DIALOG_OK:
        return None
    files = picker.getFiles()
    return files[0] if files else None


def choose_save_markdown(ctx, default_name):
    picker = _picker(
        ctx, FILESAVE_AUTOEXTENSION, "Markdown", MARKDOWN_EXTENSIONS, default_name)
    if picker.execute() != DIALOG_OK:
        return None
    files = picker.getFiles()
    return files[0] if files else None


# ---------------------------------------------------------------------- #
# Commands
# ---------------------------------------------------------------------- #
def open_dialog(ctx, frame=None):
    url = choose_open_markdown(ctx)
    if url:
        load_markdown(ctx, url)


def export_dialog(ctx, model):
    default = default_name(model)
    url = choose_save_markdown(ctx, default)
    if url:
        export_markdown(model, url)


def default_name(model):
    try:
        title = model.getURL()
    except Exception:
        title = ""
    base = title.rsplit("/", 1)[-1] if title else "document"
    if "." in base:
        base = base.rsplit(".", 1)[0]
    return base + ".md"
