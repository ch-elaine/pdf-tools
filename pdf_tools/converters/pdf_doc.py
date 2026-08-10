"""PDFs: nothing to convert, just merge them in."""

from __future__ import annotations

import pymupdf

from ..errors import ProcessingError
from .base import Context, Converter, Upload


def append_pdf(doc: pymupdf.Document, blob: bytes, name: str) -> None:
    """Append every page of `blob` to `doc`, or explain why it cannot be read.

    Shared with converters that reach a PDF by other means (Office, for example).
    """
    try:
        src = pymupdf.open(stream=blob, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ProcessingError(f"{name} is not a readable PDF.") from exc
    with src:
        if src.needs_pass:
            raise ProcessingError(f"{name} is password protected.")
        if not src.page_count:
            raise ProcessingError(f"{name} has no pages.")
        doc.insert_pdf(src)


class PdfConverter(Converter):
    name = "pdf"
    extensions = frozenset({".pdf"})

    def add_pages(self, doc: pymupdf.Document, upload: Upload, ctx: Context) -> None:
        append_pdf(doc, upload.data, upload.name)
