"""HTML: laid out with real headings, lists and emphasis by PyMuPDF's Story."""

from __future__ import annotations

import io

import pymupdf

import config

from ..layout import portrait_rect
from .base import Context, Converter, Upload
from .text import MARGIN, add_text_pages, decode


class HtmlConverter(Converter):
    name = "html"
    extensions = frozenset({".html", ".htm"})

    def add_pages(self, doc: pymupdf.Document, upload: Upload, ctx: Context) -> None:
        paper = portrait_rect()
        area = pymupdf.Rect(
            MARGIN, MARGIN, paper.width - MARGIN, paper.height - MARGIN
        )
        try:
            # Story renders into a document of its own, which is then merged in;
            # a DocumentWriter cannot append to an already-open Document.
            story = pymupdf.Story(html=decode(upload.data, upload.name))
            buf = io.BytesIO()
            writer = pymupdf.DocumentWriter(buf)
            more, pages = True, 0
            while more and pages < config.HTML_MAX_PAGES:
                device = writer.begin_page(paper)
                more, _ = story.place(area)
                story.draw(device)
                writer.end_page()
                pages += 1
            writer.close()
            with pymupdf.open(stream=buf.getvalue(), filetype="pdf") as rendered:
                if not rendered.page_count:
                    raise ValueError("story produced no pages")
                doc.insert_pdf(rendered)
        except Exception:  # noqa: BLE001 - layout is best-effort; text always works
            ctx.note(f"{upload.name}: rendered as plain text")
            add_text_pages(doc, upload.data, upload.name, ctx)
