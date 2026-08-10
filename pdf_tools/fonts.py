"""Font selection and line wrapping for text pages.

Exactly two fonts, both fixed, with nothing to configure and no system fonts to
hunt for:

* Courier, one of the base-14 fonts every PDF reader already has. It needs no
  embedding, so plain-Latin text PDFs stay tiny.
* Cascadia Mono, shipped by the `pymupdf-fonts` package, embedded only when the
  text needs glyphs Courier lacks. It is monospaced and covers Latin, Greek,
  Cyrillic, Arabic, Hebrew and box drawing.

Characters neither font has - CJK and emoji, mainly - become `?`, and the
response says so.
"""

from __future__ import annotations

import textwrap

import pymupdf

import config

#: Base-14, never embedded.
BASE_FONT = "cour"
#: From pymupdf-fonts, embedded only when Courier cannot render the text.
UNICODE_FONT = "cascadia"

FONT_SIZE = config.TEXT_FONT_SIZE
LINE_HEIGHT = config.TEXT_LINE_HEIGHT


class TextFont:
    """A font usable by both the measurer (pymupdf.Font) and the page writer."""

    def __init__(self, fontname: str, fontfile: str | None = None, *, packaged: bool = False):
        self.fontname = fontname
        self.fontfile = fontfile
        if fontfile:
            self.font = pymupdf.Font(fontfile=fontfile)
        else:
            self.font = pymupdf.Font(fontname)
        # A packaged font has to travel with the page as a buffer; base-14 does not.
        self.buffer = self.font.buffer if packaged else None
        self._glyphs: dict[str, bool] = {}

    def register(self, page: pymupdf.Page) -> None:
        """Add this font to a page's resources.

        Call once per new page: insert_text() only takes a font *name*, so an
        embedded font has to be registered on the page before it can be named.
        Base-14 fonts need nothing.
        """
        if self.buffer is None and not self.fontfile:
            return
        page.insert_font(
            fontname=self.fontname, fontfile=self.fontfile, fontbuffer=self.buffer
        )

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
                    keep = ch in "\n\t" or bool(self.font.has_glyph(ord(ch)))
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
    """Courier: always available, never embedded."""
    font = _cache.get("base14")
    if font is None:
        font = _cache["base14"] = TextFont(BASE_FONT)
    return font


def unicode_font() -> TextFont | None:
    """The embedded wide-coverage font, or None if it cannot be loaded."""
    if "unicode" in _cache:
        return _cache["unicode"]
    _cache["unicode"] = None
    try:
        _cache["unicode"] = TextFont(UNICODE_FONT, packaged=True)
    except Exception:  # noqa: BLE001 - pymupdf-fonts missing; Courier still works
        pass
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
