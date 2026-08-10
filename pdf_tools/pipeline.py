"""The one pipeline every upload goes through.

    1. dispatch  - each file is handed to the converter that claims its extension,
                   which appends pages to a single document (upload order kept)
    2. normalise - every page is put onto the configured paper size
    3. merge     - that document is serialised once
    4. compress  - oversized images are downsampled and re-encoded, fonts are
                   subset, streams are deflated and the xref is cleaned

Formats live in `converters/`; this module knows nothing about any of them.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from . import converters, layout
from .compress import compress, save
from .converters import Context, Upload
from .errors import ProcessingError
from .memory import release_caches
from .quality import Quality, resolve


@dataclass
class Result:
    data: bytes
    filename: str
    original_bytes: int
    pages: int
    quality: Quality
    notes: list[str] = field(default_factory=list)


def _output_name(names: list[str]) -> str:
    if len(names) == 1:
        return f"{Path(names[0]).stem or 'document'}_compressed.pdf"
    return "combined_compressed.pdf"


def build_pdf(files: Iterable[tuple[str, bytes]], dpi: object = None) -> Result:
    """Merge every upload into one PDF, all on one paper size, and compress it.

    `files` yields (filename, bytes) in the order the user picked them. It may be
    a generator, and should be: each upload's bytes are released as soon as its
    pages are on paper, so peak memory tracks the largest single file plus the
    document being built rather than the whole batch.

    `dpi` is the slider value; None uses the configured default.
    """
    profile = resolve(dpi)
    ctx = Context(quality=profile)
    names: list[str] = []
    original_bytes = 0
    #: Kept only while this is a single-file job, for the "unchanged" fallback.
    solo_blob: bytes | None = None

    out = pymupdf.open()
    resized = None
    try:
        for name, blob in files:
            names.append(name)
            original_bytes += len(blob)
            solo_blob = blob if len(names) == 1 else None

            if not blob:
                ctx.note(f"{name}: skipped, file is empty")
                continue
            upload = Upload(name=name, data=blob, suffix=Path(name).suffix.lower())
            converter = converters.for_suffix(upload.suffix)
            if converter is None:
                raise ProcessingError(
                    f"{name}: unsupported file type "
                    f"({upload.suffix or 'no extension'})."
                )
            converter.add_pages(out, upload, ctx)
            del upload, blob  # let this upload go before reading the next one

        if not names:
            raise ProcessingError("No files were uploaded.")
        if len(names) == 1 and not original_bytes:
            raise ProcessingError(f"{names[0]} is empty.")

        if not out.page_count:
            raise ProcessingError("Nothing could be turned into PDF pages.")

        # Merging is what mangles jump destinations, so repair before resizing.
        layout.repair_destinations(out)

        # Pages built by our own converters are already the right size, so this
        # only rebuilds when an incoming PDF used different paper.
        resized, changed = layout.normalize(out)
        doc = resized or out
        if changed:
            ctx.note(f"{changed} page(s) resized to {layout.name()}")

        release_caches()
        doc.set_metadata({"producer": "pdf-tools", "creator": "pdf-tools"})
        pages = doc.page_count
        merged = save(doc)
    finally:
        if resized is not None:
            with suppress(Exception):
                resized.close()
        out.close()

    data = compress(merged, profile, ctx.notes)

    # A single already-optimised PDF must never come back bigger than it went in,
    # unless resizing it to the target paper was the point.
    if (
        solo_blob is not None
        and names[0].lower().endswith(".pdf")
        and len(data) >= original_bytes
        and not any("resized" in note for note in ctx.notes)
    ):
        ctx.note("already optimised - returned unchanged")
        data = solo_blob

    return Result(
        data=data,
        filename=_output_name(names),
        original_bytes=original_bytes,
        pages=pages,
        quality=profile,
        notes=ctx.notes,
    )
