"""Font selection and line wrapping for text pages.

Base-14 fonts need no embedding, which keeps plain-Latin PDFs tiny, so they are
preferred. A system Unicode TTF is embedded only when the text actually needs
glyphs Courier does not have. No font is required to be present: the base-14
path always works, and PyMuPDF ships it.

Sizes, margins and the font search list live in config.py.
"""

from __future__ import annotations

import os
import textwrap

import pymupdf

import config

FONT_SIZE = config.TEXT_FONT_SIZE
LINE_HEIGHT = config.TEXT_LINE_HEIGHT


class TextFont:
    """A font usable by both the measurer (pymupdf.Font) and the page writer."""

    def __init__(self, fontname: str, fontfile: str | None) -> None:
        self.fontname = fontname
        self.fontfile = fontfile
        self.font = pymupdf.Font(fontfile=fontfile) if fontfile else pymupdf.Font(fontname)
        self._glyphs: dict[str, bool] = {}

    def width(self, text: str, size: float = FONT_SIZE) -> float:
        return self.font.text_length(text, fontsize=size)

    def sanitize(self, text: str) -> tuple[str, bool]:
        """Replace glyphs the font lacks so they don't silently vanish."""
        out: list[str] = []
        dropped = False
        for ch in text:
            keep = self._glyphs.get(ch)
            if keep is None:
                try:
                    keep = ch in "\n\t" or self.font.has_glyph(ord(ch))
                except Exception:  # noqa: BLE001
                    keep = True
                self._glyphs[ch] = keep
            if keep:
                out.append(ch)
            else:
                out.append("?")
                dropped = True
        return "".join(out), dropped


_cache: dict[str, TextFont | None] = {}


def base14() -> TextFont:
    font = _cache.get("base14")
    if font is None:
        font = _cache["base14"] = TextFont("cour", None)
    return font


def unicode_font() -> TextFont | None:
    """The first usable Unicode font, or None if the host has none installed."""
    if "unicode" in _cache:
        return _cache["unicode"]
    _cache["unicode"] = None
    # TEXT_FONT wins: any .ttf works, including scripts the defaults don't cover.
    override = (config.TEXT_FONT,) if config.TEXT_FONT else ()
    for path in override + config.UNICODE_FONT_CANDIDATES:
        if not os.path.isfile(path):
            continue
        try:
            _cache["unicode"] = TextFont("uni", path)
        except Exception:  # noqa: BLE001 - unusable font file, try the next one
            continue
        break
    return _cache["unicode"]


def pick(text: str) -> TextFont:
    """Cheapest font that can render this text."""
    if text.isascii():
        return base14()
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        return unicode_font() or base14()
    return base14()


def wrap(line: str, font: TextFont, max_width: float) -> list[str]:
    """Break one source line into rows that fit `max_width` points."""
    line = line.expandtabs(config.TEXT_TAB_WIDTH).rstrip()
    if not line:
        return [""]
    if font.width(line) <= max_width:
        return [line]

    rows: list[str] = []
    guess = max(8, int(max_width / max(font.width("0"), 0.1)))
    for chunk in textwrap.wrap(
        line,
        width=guess,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=False,
        drop_whitespace=False,
    ) or [""]:
        # textwrap counts characters; proportional fonts still need a real check.
        while font.width(chunk) > max_width and len(chunk) > 1:
            cut = max(1, int(len(chunk) * max_width / font.width(chunk)))
            rows.append(chunk[:cut])
            chunk = chunk[cut:]
        rows.append(chunk)
    return rows
