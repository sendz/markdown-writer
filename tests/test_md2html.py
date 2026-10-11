import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "pythonpath"))

from mdwriter.md2html import to_html, html_document

md = (
    "# Title\n"
    "\n"
    "Hello **bold**, *italic*, `code` and [a link](http://example.com).\n"
    "\n"
    "- one\n"
    "- two\n"
    "\n"
    "1. first\n"
    "2. second\n"
    "\n"
    "> a quote\n"
    "\n"
    "```\nprint('hi')\n```\n"
    "\n"
    "---\n"
)

out = to_html(md)

cases = [
    ("<h1>Title</h1>", "<h1>Title</h1>" in out),
    ("bold", "<strong>bold</strong>" in out),
    ("italic", "<em>italic</em>" in out),
    ("code", "<code>code</code>" in out),
    ("link", '<a href="http://example.com">a link</a>' in out),
    ("ul", "<ul>" in out and "<li>one</li>" in out and "<li>two</li>" in out),
    ("ol", "<ol>" in out and "<li>first</li>" in out),
    ("blockquote", "<blockquote>" in out and "<p>a quote</p>" in out),
    ("code block", "<pre><code>" in out and "hi" in out),
    ("hr", "<hr/>" in out),
]

failures = 0
for label, cond in cases:
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        failures += 1

doc = html_document("# Hi")
if "<!DOCTYPE html>" not in doc or "<h1>Hi</h1>" not in doc:
    print("FAIL  html_document")
    failures += 1
else:
    print("PASS  html_document")

print()
if failures:
    print("----- output -----")
    print(out)
    print("RESULT: %d FAILURES" % failures)
    sys.exit(1)
print("RESULT: ALL PASS")
