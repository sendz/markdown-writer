"""Minimal Markdown -> HTML converter (no external dependencies).

It covers the subset of Markdown that Markdown Writer produces: headings,
paragraphs, bullet/numbered lists, block quotes, fenced code blocks, horizontal
rules and the inline markers handled by :mod:`mdwriter.markdown`.
"""

import html

from mdwriter.markdown import (
    HEADING_RE,
    BULLET_RE,
    NUMBER_RE,
    QUOTE_RE,
    FENCE_RE,
    split_inline,
)


def inline_to_html(text):
    """Render inline Markdown *text* as HTML (escaping is applied)."""
    plain, spans = split_inline(text)
    out = []
    cursor = 0
    for start, end, kind, payload in spans:
        out.append(html.escape(plain[cursor:start]))
        content = html.escape(plain[start:end])
        if kind == "bold":
            out.append("<strong>%s</strong>" % content)
        elif kind == "italic":
            out.append("<em>%s</em>" % content)
        elif kind == "code":
            out.append("<code>%s</code>" % content)
        elif kind == "strike":
            out.append("<del>%s</del>" % content)
        elif kind == "link":
            out.append('<a href="%s">%s</a>' % (html.escape(payload, quote=True), content))
        cursor = end
    out.append(html.escape(plain[cursor:]))
    return "".join(out)


def to_html(markdown_text):
    """Convert *markdown_text* to an HTML body fragment."""
    lines = markdown_text.split("\n")
    out = []
    list_kind = None       # "ul" / "ol" / None
    in_quote = False
    in_code = False

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append("</%s>" % list_kind)
            list_kind = None

    def close_quote():
        nonlocal in_quote
        if in_quote:
            out.append("</blockquote>")
            in_quote = False

    for line in lines:
        if FENCE_RE.match(line.strip()):
            close_list()
            close_quote()
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                out.append("<pre><code>")
                in_code = True
            continue

        if in_code:
            out.append(html.escape(line))
            continue

        stripped = line.strip()
        if not stripped:
            close_list()
            close_quote()
            continue

        heading = HEADING_RE.match(stripped)
        if heading:
            close_list()
            close_quote()
            level = len(heading.group(1))
            out.append("<h%d>%s</h%d>" % (
                level, inline_to_html(heading.group(2)), level))
            continue

        if stripped in ("---", "***", "___"):
            close_list()
            close_quote()
            out.append("<hr/>")
            continue

        quote = QUOTE_RE.match(stripped)
        if quote:
            close_list()
            if not in_quote:
                out.append("<blockquote>")
                in_quote = True
            out.append("<p>%s</p>" % inline_to_html(quote.group(1)))
            continue
        close_quote()

        bullet = BULLET_RE.match(stripped)
        number = NUMBER_RE.match(stripped)
        if bullet or number:
            wanted = "ul" if bullet else "ol"
            if list_kind != wanted:
                close_list()
                out.append("<%s>" % wanted)
                list_kind = wanted
            content = bullet.group(1) if bullet else number.group(1)
            out.append("<li>%s</li>" % inline_to_html(content))
            continue

        close_list()
        out.append("<p>%s</p>" % inline_to_html(stripped))

    close_list()
    close_quote()
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def html_document(markdown_text, title="Markdown Preview"):
    """Wrap the converted Markdown in a small standalone HTML document."""
    return (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">\n"
        "<title>%s</title>\n"
        "<style>body{font-family:sans-serif;max-width:46em;margin:2em auto;"
        "padding:0 1em;line-height:1.5;color:#222}"
        "code{font-family:monospace;background:#f2f2f2;padding:0 .2em}"
        "pre{background:#f6f8fa;padding:1em;overflow:auto}"
        "blockquote{border-left:3px solid #ddd;margin-left:0;padding-left:1em;"
        "color:#555}</style>\n"
        "</head>\n<body>\n%s\n</body></html>\n"
        % (html.escape(title), to_html(markdown_text))
    )
