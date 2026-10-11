#!/usr/bin/env python3
"""Integration tests for the Markdown Writer extension.

Run through ``tests/run_tests.sh`` which starts a headless LibreOffice with a
UNO socket. Can also be run manually against an already running office:

    MARKDOWN_WRITER_PORT=2002 python3 tests/uno_tests.py

The tests exercise the extension the same way LibreOffice does: they resolve
the component context over the bridge, instantiate the protocol handler and
call the formatter functions on real documents.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "pythonpath"))

import uno  # noqa: E402

HOST = os.environ.get("MARKDOWN_WRITER_HOST", "localhost")
PORT = os.environ.get("MARKDOWN_WRITER_PORT", "2002")

FAILURES = []


def check(label, condition):
    print(("  PASS  " if condition else "  FAIL  ") + label)
    if not condition:
        FAILURES.append(label)


def connect():
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    url = "uno:socket,host=%s,port=%s;urp;StarOffice.ComponentContext" % (HOST, PORT)
    return resolver.resolve(url)


def test_registration(ctx):
    print("== registration ==")
    d = ctx.ServiceManager.createInstanceWithContext(
        "com.sendyyeah.mdwriter.Dispatch", ctx)
    check("component instantiation",
          d.getImplementationName() == "com.sendyyeah.mdwriter.Dispatch")
    check("provides ProtocolHandler service",
          d.supportsService("com.sun.star.frame.ProtocolHandler"))

    url = uno.createUnoStruct("com.sun.star.util.URL")
    url.Protocol = "service:"
    url.Complete = "service:com.sendyyeah.mdwriter.Dispatch?command=about"
    check("queryDispatch returns a dispatch",
          d.queryDispatch(url, "_self", 0) is not None)


def test_formatter(ctx):
    from mdwriter import formatter

    desktop = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
    text = doc.getText()
    cur = text.createTextCursor()
    text.insertString(cur, "Hello world", False)
    text.insertControlCharacter(cur, uno.getConstantByName(
        "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK"), False)
    text.insertString(cur, "Second paragraph", False)
    controller = doc.getCurrentController()

    def set_sel(a, b):
        vc = controller.getViewCursor()
        vc.gotoStart(False)
        vc.goRight(a, False)
        vc.goRight(b - a, True)

    def read_prop(prop, a, b):
        r = text.createTextCursor()
        r.gotoStart(False)
        r.goRight(a, False)
        r.goRight(b - a, False)
        return r.getPropertyValue(prop)

    print("== character formatting ==")
    set_sel(0, 5)
    formatter.toggle_bold(ctx, doc)
    check("bold applied", float(read_prop("CharWeight", 0, 5)) >= 149)
    formatter.toggle_bold(ctx, doc)
    check("bold removed", float(read_prop("CharWeight", 0, 5)) < 149)

    set_sel(0, 5)
    formatter.toggle_italic(ctx, doc)
    check("italic applied", "ITALIC" in str(read_prop("CharPosture", 0, 5)))
    formatter.toggle_italic(ctx, doc)

    set_sel(0, 5)
    formatter.toggle_strike(ctx, doc)
    check("strike applied", int(read_prop("CharStrikeout", 0, 5)) == 1)
    formatter.toggle_strike(ctx, doc)
    check("strike removed", int(read_prop("CharStrikeout", 0, 5)) == 0)

    set_sel(0, 5)
    formatter.toggle_code(ctx, doc)
    check("inline code applied", read_prop("CharStyleName", 0, 5) == "Source Text")
    formatter.toggle_code(ctx, doc)
    check("inline code removed", read_prop("CharStyleName", 0, 5) != "Source Text")

    print("== paragraph formatting ==")
    set_sel(0, 0)
    formatter.set_heading(ctx, doc, 2)
    check("heading 2", read_prop("ParaStyleName", 0, 1) == "Heading 2")
    formatter.set_body(ctx, doc)
    check("body text", read_prop("ParaStyleName", 0, 1) == "Text body")
    formatter.toggle_quote(ctx, doc)
    check("block quote", read_prop("ParaStyleName", 0, 1) == "Quotations")
    formatter.toggle_quote(ctx, doc)
    formatter.toggle_code_block(ctx, doc)
    check("code block", read_prop("ParaStyleName", 0, 1) == "Preformatted Text")
    formatter.toggle_code_block(ctx, doc)
    formatter.insert_rule(ctx, doc)
    check("horizontal rule", read_prop("ParaStyleName", 0, 1) == "Horizontal Line")
    formatter.set_body(ctx, doc)

    print("== lists and table ==")
    set_sel(0, 0)
    try:
        formatter.toggle_bullet_list(ctx, doc)
        check("bullet list", True)
    except Exception as exc:
        check("bullet list (%s)" % exc, False)
    try:
        formatter.insert_table(ctx, doc)
        check("table inserted", doc.getTextTables().hasElements())
    except Exception as exc:
        check("table inserted (%s)" % exc, False)

    doc.close(False)


def test_export_import(ctx):
    from mdwriter import exporter
    import tempfile

    desktop = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)

    print("== export ==")
    doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
    text = doc.getText()
    cur = text.createTextCursor()
    text.insertString(cur, "Title", False)
    cur.setPropertyValue("ParaStyleName", "Heading 1")
    text.insertControlCharacter(cur, uno.getConstantByName(
        "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK"), False)
    text.insertString(cur, "Some ", False)
    text.insertString(cur, "bold", False)
    cur.goLeft(4, True)
    cur.setPropertyValue("CharWeight", 150.0)

    md_file = tempfile.mktemp(suffix=".md", dir="/tmp")
    exporter.export_markdown(doc, uno.systemPathToFileUrl(md_file))
    doc.close(False)

    with open(md_file, encoding="utf-8") as handle:
        content = handle.read()
    check("exported heading", "# Title" in content)
    check("exported bold", "**bold**" in content)

    print("== import ==")
    doc2 = exporter.load_markdown(ctx, uno.systemPathToFileUrl(md_file))
    c = doc2.getText().createTextCursor()
    c.gotoStart(False)
    c.gotoEndOfParagraph(True)
    check("imported heading text", c.getString() == "Title")
    check("imported heading style",
          c.getPropertyValue("ParaStyleName") == "Heading 1")
    doc2.close(False)


def test_dispatch_command(ctx):
    """Commands must work through the add-on UI path (frame -> ServiceHandler)."""
    print("== dispatch command (add-on UI path) ==")
    desktop = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
    text = doc.getText()
    cur = text.createTextCursor()
    text.insertString(cur, "Hello", False)
    controller = doc.getCurrentController()
    vc = controller.getViewCursor()
    vc.gotoStart(False)
    vc.goRight(5, True)

    url = uno.createUnoStruct("com.sun.star.util.URL")
    url.Protocol = "service:"
    url.Complete = "service:com.sendyyeah.mdwriter.Dispatch?command=bold"

    # This is exactly what the menu/toolbar does: ask the frame, which routes
    # "service:" URLs through com.sun.star.comp.framework.ServiceHandler, which
    # creates the component and calls XJobExecutor.trigger().
    dispatch = desktop.getCurrentFrame().queryDispatch(url, "_self", 0)
    check("frame resolves the command", dispatch is not None)
    dispatch.dispatch(url, ())

    check_cursor = text.createTextCursor()
    check_cursor.gotoStart(False)
    check_cursor.goRight(5, False)
    check("bold applied through the add-on UI path",
          float(check_cursor.getPropertyValue("CharWeight")) >= 149)
    doc.close(False)


def test_preview(ctx):
    from mdwriter import preview

    desktop = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
    text = doc.getText()
    cur = text.createTextCursor()
    text.insertString(cur, "Heading", False)
    cur.setPropertyValue("ParaStyleName", "Heading 1")

    print("== preview rendering ==")
    md = preview.document_to_markdown(doc, "/tmp/mdwriter-test-preview.md")
    check("document rendered to markdown", "# Heading" in md)
    html_path = preview.markdown_to_html_file(md, "/tmp/mdwriter-test-preview.html")
    with open(html_path, encoding="utf-8") as handle:
        html_text = handle.read()
    check("markdown rendered to html", "<h1>Heading</h1>" in html_text)

    print("== apply source to document ==")
    preview._apply_source(ctx, doc, "# New Title\n\nSome **bold** text.")
    c = text.createTextCursor()
    c.gotoStart(False)
    c.gotoEndOfParagraph(True)
    check("applied heading text", c.getString() == "New Title")
    check("applied heading style",
          c.getPropertyValue("ParaStyleName") == "Heading 1")

    print("== source editor dialog ==")
    dialog, control = preview._build_source_dialog(ctx, None, "# Source\n\n**bold**")
    check("dialog shows the source text",
          control.getText() == "# Source\n\n**bold**")
    check("dialog has preview, apply and close buttons",
          dialog.getControl("preview") is not None
          and dialog.getControl("apply") is not None
          and dialog.getControl("close") is not None)
    dialog.dispose()
    doc.close(False)


def main():
    ctx = connect()
    test_registration(ctx)
    test_formatter(ctx)
    test_export_import(ctx)
    test_dispatch_command(ctx)
    test_preview(ctx)
    print()
    if FAILURES:
        print("RESULT: %d FAILURE(S): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
