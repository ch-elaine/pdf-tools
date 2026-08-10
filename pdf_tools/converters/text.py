"""Plain text, code, CSV, config: monospaced pages with real, selectable text."""

from __future__ import annotations

import pymupdf

import config

from .. import fonts
from ..errors import ProcessingError
from ..layout import PORTRAIT
from .base import Context, Converter, Upload

MARGIN = config.TEXT_MARGIN
PAGE_WIDTH, PAGE_HEIGHT = PORTRAIT


def decode(blob: bytes, name: str) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return blob.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ProcessingError(f"Could not read {name} as text.")


def add_text_pages(doc: pymupdf.Document, blob: bytes, name: str, ctx: Context) -> None:
    """Lay text out over as many pages as it needs. Shared with the HTML fallback."""
    text = decode(blob, name).replace("\r\n", "\n").replace("\r", "\n")
    font = fonts.pick(text)
    if not text.isascii():
        text, dropped = font.sanitize(text)
        if dropped:
            ctx.note(f"{name}: some characters are missing from the available font")

    max_width = PAGE_WIDTH - 2 * MARGIN
    step = fonts.FONT_SIZE * fonts.LINE_HEIGHT
    bottom = PAGE_HEIGHT - MARGIN

    rows: list[str] = []
    for line in text.split("\n"):
        rows.extend(fonts.wrap(line, font, max_width))

    page = None
    y = 0.0
    for row in rows:
        if page is None or y > bottom:
            page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            y = MARGIN + fonts.FONT_SIZE
        if row:
            page.insert_text(
                (MARGIN, y),
                row,
                fontsize=fonts.FONT_SIZE,
                fontname=font.fontname,
                fontfile=font.fontfile,
            )
        y += step
    if page is None:  # whitespace-only input: keep a page so nothing vanishes
        doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)


class TextConverter(Converter):
    name = "text"
    extensions = frozenset({
        ".txt", ".text", ".md", ".markdown", ".rst", ".log", ".csv", ".tsv",
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env",
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".h", ".cpp", ".hpp",
        ".cs", ".go", ".rs", ".rb", ".php", ".sh", ".bash", ".zsh", ".sql",
        ".xml", ".svg", ".css", ".scss", ".tex", ".srt", ".vtt",
    })

    def add_pages(self, doc: pymupdf.Document, upload: Upload, ctx: Context) -> None:
        add_text_pages(doc, upload.data, upload.name, ctx)
