"""Markdown formatting operations for Writer documents.

Every function has the signature ``func(ctx, model)`` where ``ctx`` is the UNO
component context and ``model`` is the current Writer document
(``com.sun.star.text.TextDocument``).

Character formatting is applied through a text cursor so it works on the
current selection (or the word under the cursor when nothing is selected).
Paragraph formatting is applied to every paragraph touched by the selection.
"""

import uno

# --- character weight -------------------------------------------------- #
BOLD_WEIGHT = 150.0
NORMAL_WEIGHT = 100.0

# --- enums ------------------------------------------------------------- #
SLANT = "com.sun.star.awt.FontSlant"

# --- style names (English UI) ------------------------------------------ #
BODY_STYLE = "Text body"
QUOTE_STYLE = "Quotations"
CODE_BLOCK_STYLE = "Preformatted Text"

CHAR_CODE_STYLE = "Source Text"
CHAR_STANDARD_STYLE = "Standard"

HEADING_STYLE = "Heading %d"


# ---------------------------------------------------------------------- #
# Low level helpers
# ---------------------------------------------------------------------- #
def is_writer(model):
    """True if *model* is a text document."""
    if model is None:
        return False
    return model.supportsService("com.sun.star.text.TextDocument")


def _enum_value(value):
    """Return the numeric value of a UNO enum, tolerant to representation."""
    try:
        return value.value
    except AttributeError:
        return None


def _slant(value):
    return uno.Enum(SLANT, value)


def _selection(model):
    """Return the current selection as a text range, or ``None``.

    ``Controller.getViewCursor()`` reflects what the user has selected (or the
    caret position when nothing is selected) and is an ``XTextViewCursor``,
    which is also an ``XTextRange``.  ``Controller.getSelection()`` is avoided
    because it may return a collection of ranges instead of a single range.
    """
    controller = model.getCurrentController()
    if controller is None:
        return None
    try:
        return controller.getViewCursor()
    except Exception:
        return None


def _char_cursor(model):
    """Cursor over the selection; a collapsed selection expands to the word."""
    text = model.getText()
    cursor = text.createTextCursorByRange(_selection(model))
    if cursor.isCollapsed():
        cursor.gotoStartOfWord(False)
        cursor.gotoEndOfWord(True)
    return cursor


def _para_cursor(model):
    """Cursor over the selection used for paragraph-level properties."""
    text = model.getText()
    return text.createTextCursorByRange(_selection(model))


def _dispatch(ctx, model, command, args=()):
    """Run a built-in ``.uno:`` command inside the document frame."""
    frame = model.getCurrentController().getFrame()
    helper = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.DispatchHelper", ctx)
    helper.executeDispatch(frame, command, "", 0, args)


# ---------------------------------------------------------------------- #
# Character formatting
# ---------------------------------------------------------------------- #
def toggle_bold(ctx, model):
    cursor = _char_cursor(model)
    try:
        current = float(cursor.getPropertyValue("CharWeight"))
    except Exception:
        current = NORMAL_WEIGHT
    bold = current >= BOLD_WEIGHT - 1
    cursor.setPropertyValue(
        "CharWeight", NORMAL_WEIGHT if bold else BOLD_WEIGHT)


def toggle_italic(ctx, model):
    cursor = _char_cursor(model)
    current = cursor.getPropertyValue("CharPosture")
    italic = _enum_value(current) == _enum_value(_slant("ITALIC"))
    cursor.setPropertyValue("CharPosture", _slant("NONE" if italic else "ITALIC"))


def toggle_strike(ctx, model):
    _dispatch(ctx, model, ".uno:Strikeout")


def toggle_code(ctx, model):
    """Toggle the inline-code character style (monospace)."""
    cursor = _char_cursor(model)
    current = cursor.getPropertyValue("CharStyleName")
    cursor.setPropertyValue(
        "CharStyleName",
        CHAR_STANDARD_STYLE if current == CHAR_CODE_STYLE else CHAR_CODE_STYLE)


# ---------------------------------------------------------------------- #
# Paragraph formatting
# ---------------------------------------------------------------------- #
def set_heading(ctx, model, level):
    cursor = _para_cursor(model)
    cursor.setPropertyValue("ParaStyleName", HEADING_STYLE % level)


def set_body(ctx, model):
    cursor = _para_cursor(model)
    cursor.setPropertyValue("ParaStyleName", BODY_STYLE)


def toggle_quote(ctx, model):
    cursor = _para_cursor(model)
    current = cursor.getPropertyValue("ParaStyleName")
    cursor.setPropertyValue(
        "ParaStyleName", BODY_STYLE if current == QUOTE_STYLE else QUOTE_STYLE)


def toggle_code_block(ctx, model):
    cursor = _para_cursor(model)
    current = cursor.getPropertyValue("ParaStyleName")
    cursor.setPropertyValue(
        "ParaStyleName",
        BODY_STYLE if current == CODE_BLOCK_STYLE else CODE_BLOCK_STYLE)


def insert_rule(ctx, model):
    """Insert a horizontal rule (single line) as its own paragraph."""
    text = model.getText()
    cursor = text.createTextCursorByRange(_selection(model))
    # Put the rule on its own (new) paragraph so existing text is untouched.
    cursor.gotoEndOfParagraph(False)
    text.insertControlCharacter(
        cursor,
        uno.getConstantByName("com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK"),
        False)
    paragraph = text.createTextCursorByRange(cursor)
    paragraph.gotoStartOfParagraph(False)
    paragraph.gotoEndOfParagraph(True)
    paragraph.setPropertyValue("ParaStyleName", BODY_STYLE)

    line = uno.createUnoStruct("com.sun.star.table.BorderLine2")
    line.LineStyle = 1        # BorderLineStyle.SOLID: a single line
    line.LineWidth = 26       # 0.26 mm
    line.Color = 0x000000
    paragraph.setPropertyValue("BottomBorder", line)
    paragraph.setPropertyValue("BottomBorderDistance", 0)


# ---------------------------------------------------------------------- #
# Lists, links, tables (built-in commands)
# ---------------------------------------------------------------------- #
def toggle_bullet_list(ctx, model):
    _dispatch(ctx, model, ".uno:DefaultBullet")


def toggle_number_list(ctx, model):
    _dispatch(ctx, model, ".uno:DefaultNumbering")


def insert_link(ctx, model):
    _dispatch(ctx, model, ".uno:InsertHyperlink")


def insert_table(ctx, model, rows=2, columns=3):
    """Insert a small table (Markdown tables are edited through this)."""
    table = model.createInstance("com.sun.star.text.TextTable")
    table.initialize(rows, columns)
    text = model.getText()
    cursor = text.createTextCursorByRange(_selection(model))
    text.insertTextContent(cursor, table, False)
