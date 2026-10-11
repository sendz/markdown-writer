"""Pure Markdown parsing helpers (no LibreOffice/UNO dependencies).

Keeping this separate makes the text transformation unit testable without a
running office.
"""

import re

# --- block level patterns ---------------------------------------------- #
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_RE = re.compile(r"^[-*+]\s+(.*)$")
NUMBER_RE = re.compile(r"^\d+\.\s+(.*)$")
QUOTE_RE = re.compile(r"^> ?(.*)$")
FENCE_RE = re.compile(r"^```\s*$")

# opening, closing, kind - longest delimiters first
INLINE_MARKERS = (
    ("**", "**", "bold"),
    ("__", "__", "bold"),
    ("~~", "~~", "strike"),
    ("`", "`", "code"),
    ("*", "*", "italic"),
    ("_", "_", "italic"),
)

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")


def split_inline(text):
    """Split *text* into ``(plain_text, spans)``.

    ``spans`` is a list of ``(start, end, kind, payload)`` tuples whose indices
    refer to *plain_text*.  Delimiters that are not closed are left untouched,
    because they are presumably still being typed.
    """
    out = []
    spans = []
    position = 0
    length = len(text)

    def current_index():
        return sum(len(part) for part in out)

    while position < length:
        link = LINK_RE.match(text, position)
        if link is not None:
            start = current_index()
            out.append(link.group(1))
            spans.append((start, start + len(link.group(1)), "link", link.group(2)))
            position = link.end()
            continue

        for opener, closer, kind in INLINE_MARKERS:
            if not text.startswith(opener, position):
                continue
            close_at = text.find(closer, position + len(opener))
            if close_at != -1 and close_at > position + len(opener):
                content = text[position + len(opener):close_at]
                start = current_index()
                out.append(content)
                spans.append((start, start + len(content), kind, None))
                position = close_at + len(closer)
                break
            # No valid closer for this opener.  If the opener is more than one
            # character long (e.g. "**"), consume it literally instead of
            # falling back to a shorter opener (the single "*") at the same
            # position - otherwise a partially typed "**bold*" would be parsed
            # as italic.
            if len(opener) > 1:
                out.append(opener)
                position += len(opener)
                break
        else:
            out.append(text[position])
            position += 1

    return "".join(out), spans
