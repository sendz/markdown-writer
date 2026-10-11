import sys
sys.path.insert(0, "/home/sendy/Projects/markdown-writer/pythonpath")
from mdwriter.markdown import split_inline, trailing_inline

cases = [
    ("**bold**", "bold", [(0, 4, "bold", None)]),
    ("a *b* c", "a b c", [(2, 3, "italic", None)]),
    ("a _b_ c", "a b c", [(2, 3, "italic", None)]),
    ("`code`", "code", [(0, 4, "code", None)]),
    ("~~gone~~", "gone", [(0, 4, "strike", None)]),
    ("[text](http://x.com)", "text", [(0, 4, "link", "http://x.com")]),
    ("mix **b** and `c` end", "mix b and c end",
     [(4, 5, "bold", None), (10, 11, "code", None)]),
    ("**unclosed", "**unclosed", []),
    ("**bold*", "**bold*", []),
    ("*bold", "*bold", []),
    ("_bold", "_bold", []),
    ("just text", "just text", []),
    ("**a** *b* `c` ~~d~~", "a b c d",
     [(0, 1, "bold", None), (2, 3, "italic", None),
      (4, 5, "code", None), (6, 7, "strike", None)]),
]

failures = 0
for text, expected_plain, expected_spans in cases:
    plain, spans = split_inline(text)
    ok = plain == expected_plain and spans == expected_spans
    print(("PASS  " if ok else "FAIL  ") + repr(text))
    if not ok:
        print("      plain=", repr(plain), "expected", repr(expected_plain))
        print("      spans=", spans, "expected", expected_spans)
        failures += 1

print()
trailing_cases = [
    ("**bold**", ("bold", 0, "bold", None, 2, 2)),
    ("a `code`", ("code", 2, "code", None, 1, 1)),
    ("x *it*", ("italic", 2, "it", None, 1, 1)),
    ("~~s~~", ("strike", 0, "s", None, 2, 2)),
    ("[t](u)", ("link", 0, "t", "u", 1, 4)),
    ("**bold*", None),
    ("*bold", None),
    ("no markers here", None),
    ("plain **b** trailing", None),
]
for text, expected in trailing_cases:
    got = trailing_inline(text)
    ok = got == expected
    print(("PASS  " if ok else "FAIL  ") + "trailing " + repr(text))
    if not ok:
        print("      got=", got, "expected=", expected)
        failures += 1

print()
print("RESULT:", "ALL PASS" if failures == 0 else "%d FAILURES" % failures)
sys.exit(1 if failures else 0)
