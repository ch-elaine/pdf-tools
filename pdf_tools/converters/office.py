"""Word/Excel/PowerPoint and friends, via LibreOffice when it is installed.

This is the one heavyweight dependency, so it stays strictly optional: without
it these uploads are refused with an explanation instead of failing obscurely.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pymupdf

import config

from ..errors import ProcessingError
from ..externals import find, run
from .base import Context, Converter, Upload
from .pdf_doc import append_pdf


class OfficeConverter(Converter):
    name = "office"
    extensions = frozenset({
        ".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods",
        ".ppt", ".pptx", ".odp", ".epub",
    })
    requires = ("soffice",)

    def add_pages(self, doc: pymupdf.Document, upload: Upload, ctx: Context) -> None:
        append_pdf(doc, self._to_pdf(upload), upload.name)

    def _to_pdf(self, upload: Upload) -> bytes:
        soffice = find("soffice")
        if not soffice:
            raise ProcessingError(
                f"{upload.name}: converting Office documents needs LibreOffice "
                "installed on the server. Export it to PDF (or a text file) and "
                "try again."
            )
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / f"input{upload.suffix}"
            src.write_bytes(upload.data)
            # A private profile dir keeps concurrent conversions from clashing.
            profile = Path(tmp) / "profile"
            result = run(
                [
                    soffice, "--headless", "--norestore", "--nolockcheck", "--nodefault",
                    f"-env:UserInstallation=file://{profile}",
                    "--convert-to", "pdf", "--outdir", tmp, str(src),
                ],
                config.SOFFICE_TIMEOUT,
            )
            pdf = src.with_suffix(".pdf")
            if not pdf.exists() or not pdf.stat().st_size:
                detail = (result.stderr or b"").decode("utf-8", "replace").strip()
                raise ProcessingError(
                    f"LibreOffice could not convert {upload.name}. {detail}".strip()
                )
            return pdf.read_bytes()
