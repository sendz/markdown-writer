#!/usr/bin/env python3
"""Generate the toolbar icons and the Addons image set (Icons.xcu).

Icons are tiny PNG bitmaps drawn from a minimal 5x7 bitmap font, so no image
library or external assets are needed. Run from the project root:

    python3 tools/make_icons.py

It writes icons/*.png and Icons.xcu.
"""

import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ICON_DIR = os.path.join(ROOT, "icons")

BASE = "org.sendyyeah.mdwriter:%s"
INK = (0x27, 0x2A, 0x33, 0xFF)          # icon colour
HIGHLIGHT = (0xC0, 0x39, 0x2B, 0xFF)    # accent (unused fallback)

# --- 5x7 bitmap font ---------------------------------------------------- #
FONT = {
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "<": ["00010", "00100", "01000", "10000", "01000", "00100", "00010"],
    ">": ["01000", "00100", "00010", "00001", "00010", "00100", "01000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    '"': ["01010", "01010", "00000", "00000", "00000", "00000", "00000"],
}


class Canvas:
    def __init__(self, size):
        self.size = size
        self.pixels = [[(0, 0, 0, 0)] * size for _ in range(size)]

    def set(self, x, y, colour):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.pixels[y][x] = colour

    def fill_rect(self, x, y, w, h, colour):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, colour)

    def hline(self, x, y, w, colour):
        for xx in range(x, x + w):
            self.set(xx, y, colour)

    def glyph(self, char, x, y, scale, colour):
        for row, bits in enumerate(FONT[char]):
            for col, bit in enumerate(bits):
                if bit == "1":
                    self.fill_rect(x + col * scale, y + row * scale, scale, scale, colour)

    def text(self, chars, scale, colour):
        width = len(chars) * 6 * scale - scale
        height = 7 * scale
        x0 = (self.size - width) // 2
        y0 = (self.size - height) // 2
        for i, ch in enumerate(chars):
            self.glyph(ch, x0 + i * 6 * scale, y0, scale, colour)

    def png(self):
        rows = []
        for row in self.pixels:
            data = bytearray()
            for (r, g, b, a) in row:
                data += bytes((r, g, b, a))
            rows.append(bytes(data))
        raw = b"".join(b"\x00" + r for r in rows)
        return _png(self.size, self.size, raw)


def _png(width, height, raw):
    def chunk(kind, data):
        body = kind + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def draw(name, size, scale):
    c = Canvas(size)
    if name == "bold":
        c.text("B", scale, INK)
    elif name == "italic":
        # slanted "I": draw the bars shifted
        c.text("I", scale, INK)
    elif name == "strike":
        c.text("S", scale, INK)
        mid = size // 2
        c.hline(2, mid, size - 4, HIGHLIGHT)
    elif name == "code":
        c.text("<>", scale, INK)
    elif name == "heading1":
        c.text("H1", scale, INK)
    elif name == "bullet":
        big = max(2, scale + 1)
        c.fill_rect(2 * scale, 2 * scale, big, big, INK)
        c.hline(5 * scale, 2 * scale + big // 2, size - 6 * scale, INK)
        c.fill_rect(2 * scale, 5 * scale, big, big, INK)
        c.hline(5 * scale, 5 * scale + big // 2, size - 6 * scale, INK)
    elif name == "quote":
        c.glyph('"', 2 * scale, 2 * scale, scale, INK)
        c.glyph('"', 2 * scale, 5 * scale, scale, INK)
        c.hline(2 * scale + 6 * scale, 2 * scale, scale, INK)
    elif name == "link":
        # two overlapping rings
        top = 3 * scale
        for dx in range(0, 6 * scale):
            c.set(3 * scale + dx, top, INK)
            c.set(3 * scale + dx, top + 5 * scale, INK)
        for dy in range(0, 5 * scale):
            c.set(3 * scale, top + dy, INK)
            c.set(3 * scale + 6 * scale, top + dy, INK)
    else:
        raise ValueError("unknown icon " + name)
    return c.png()


def main():
    os.makedirs(ICON_DIR, exist_ok=True)
    entries = []
    size, big = 16, 26
    for name in ("bold", "italic", "strike", "code", "heading1",
                 "bullet", "quote", "link"):
        small_png = draw(name, size, 2)
        big_png = draw(name, big, 3)
        with open(os.path.join(ICON_DIR, "%s.png" % name), "wb") as handle:
            handle.write(small_png)
        entries.append((name, small_png, big_png))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<oor:component-data xmlns:oor="http://openoffice.org/2001/registry"',
             '                    xmlns:xs="http://www.w3.org/2001/XMLSchema"',
             '                    oor:name="Addons" oor:package="org.openoffice.Office">',
             '  <node oor:name="AddonUI">',
             '    <node oor:name="Images">']
    for name, small_png, big_png in entries:
        lines += [
            '      <node oor:name="mdw_%s" oor:op="replace">' % name,
            '        <prop oor:name="URL" oor:type="xs:string">',
            '          <value>%s</value>' % (BASE % name),
            '        </prop>',
            '        <node oor:name="UserDefinedImages">',
            '          <prop oor:name="ImageSmall" oor:type="xs:hexBinary">',
            '            <value>%s</value>' % small_png.hex().upper(),
            '          </prop>',
            '          <prop oor:name="ImageBig" oor:type="xs:hexBinary">',
            '            <value>%s</value>' % big_png.hex().upper(),
            '          </prop>',
            '        </node>',
            '      </node>',
        ]
    lines += ['    </node>', '  </node>', '</oor:component-data>', '']

    with open(os.path.join(ROOT, "Icons.xcu"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print("wrote %d icons and Icons.xcu" % len(entries))


if __name__ == "__main__":
    main()
