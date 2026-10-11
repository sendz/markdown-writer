"""Integration test for live Markdown auto-formatting.

Flow exercised (the real one a user gets):

1. The user runs a Markdown Writer command  -> the office-side Dispatch
   installs the global document watcher.
2. The user opens/creates another Writer document -> the watcher attaches the
   live listener automatically.
3. Typing Markdown in that document reformats it as you go.
"""

import os
import sys
import time

import uno

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
    return resolver.resolve(
        "uno:socket,host=%s,port=%s;urp;StarOffice.ComponentContext" % (HOST, PORT))


def main():
    ctx = connect()
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

    # -- 1. run a command once to install the watcher ------------------ #
    doc_a = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
    time.sleep(0.5)
    url = uno.createUnoStruct("com.sun.star.util.URL")
    url.Protocol = "service:"
    url.Complete = "service:com.sendyyeah.mdwriter.Dispatch?command=bold"
    dispatch = desktop.getCurrentFrame().queryDispatch(url, "_self", 0)
    dispatch.dispatch(url, ())
    time.sleep(0.5)

    # -- 2. a brand new document should be picked up automatically ----- #
    doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
    time.sleep(1.0)
    text = doc.getText()
    controller = doc.getCurrentController()

    def vc():
        return controller.getViewCursor()

    def type_text(s):
        text.insertString(vc(), s, False)
        time.sleep(0.25)

    def new_paragraph():
        text.insertControlCharacter(vc(), uno.getConstantByName(
            "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK"), False)
        time.sleep(0.25)

    def para_cursor(index):
        c = text.createTextCursor()
        c.gotoStart(False)
        for _ in range(index):
            c.gotoNextParagraph(False)
        return c

    def para_text(index):
        c = para_cursor(index)
        c.gotoStartOfParagraph(False)
        c.gotoEndOfParagraph(True)
        return c.getString()

    def para_style(index):
        return para_cursor(index).getPropertyValue("ParaStyleName")

    print("== live typing on a freshly opened document ==")
    type_text("# Hello world")
    check("heading marker consumed", para_text(0) == "Hello world")
    check("heading style applied", para_style(0) == "Heading 1")

    new_paragraph()
    type_text("- item one")
    check("bullet marker consumed", para_text(1) == "item one")

    new_paragraph()
    type_text("> quoted")
    check("quote marker consumed", para_text(2) == "quoted")
    check("quote style applied", para_style(2) == "Quotations")

    new_paragraph()
    type_text("Some **bold** text")
    check("bold markers consumed", "**" not in para_text(3))
    c = para_cursor(3)
    c.gotoStartOfParagraph(False)
    c.goRight(5, False)   # "Some "
    c.goRight(4, True)    # "bold"
    check("bold applied", float(c.getPropertyValue("CharWeight")) >= 149)

    new_paragraph()
    type_text("use `code` here")
    check("code markers consumed", "`" not in para_text(4))
    c = para_cursor(4)
    c.gotoStartOfParagraph(False)
    c.goRight(4, False)   # "use "
    c.goRight(4, True)    # "code"
    check("inline code style applied",
          c.getPropertyValue("CharStyleName") == "Source Text")

    check("bullet numbering applied",
          para_cursor(1).getPropertyValue("NumberingStyleName") == "List 1")

    new_paragraph()
    type_text("1. first")
    check("number marker consumed", para_text(5) == "first")
    check("number numbering applied",
          para_cursor(5).getPropertyValue("NumberingStyleName") == "Numbering 123")

    new_paragraph()
    type_text("```")
    check("code fence consumed", para_text(6) == "")
    check("code fence -> preformatted", para_style(6) == "Preformatted Text")

    doc.close(False)
    doc_a.close(False)

    print()
    if FAILURES:
        print("RESULT: %d FAILURE(S): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
