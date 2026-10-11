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


def trailing_inline(text):
    """Find a complete inline pattern at the *end* of *text*.

    Returns ``(kind, start, inner, payload, prefix_len, suffix_len)`` where
    *inner* is the text inside the markers, ``start`` is the index of the
    opening marker, and prefix/suffix_len are how many marker characters to
    remove on each side.  Returns ``None`` if the text does not end with a
    complete pattern.

    Live formatting uses this instead of parsing the whole paragraph, so it
    only edits the marker characters and never disturbs the formatting of the
    rest of the line.
    """
    link = LINK_RE.search(text)
    if link is not None and link.end() == len(text):
        inner = link.group(1)
        return ("link", link.start(), inner, link.group(2), 1,
                len(text) - link.start() - 1 - len(inner))

    for opener, closer, kind in (("**", "**", "bold"), ("__", "__", "bold"),
                                 ("~~", "~~", "strike")):
        if text.endswith(closer) and len(text) > 2 * len(opener):
            open_at = text.rfind(opener, 0, len(text) - len(closer))
            if open_at != -1:
                inner = text[open_at + len(opener):len(text) - len(closer)]
                if inner and opener not in inner:
                    return (kind, open_at, inner, None, len(opener), len(closer))

    for opener, closer, kind in (("`", "`", "code"), ("*", "*", "italic"),
                                 ("_", "_", "italic")):
        if not text.endswith(closer) or len(text) <= 2:
            continue
        idx = text.rfind(opener, 0, len(text) - len(closer))
        while idx != -1:
            lone = (idx == 0 or text[idx - 1] != opener) and \
                   (idx + 1 >= len(text) or text[idx + 1] != opener)
            inner = text[idx + 1:len(text) - len(closer)]
            if lone and inner and opener not in inner:
                return (kind, idx, inner, None, 1, len(closer))
            idx = text.rfind(opener, 0, idx)

    return None


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
