"""Keeping peak memory in check.

MuPDF caches page resources aggressively: asking where an image sits on a page,
or drawing one page onto another, makes it build and keep a display list holding
roughly a full-page bitmap. Over a long document that dwarfs everything else, and
none of it is needed once the page is done - so it gets purged as work proceeds.

Measured on a 120 MB upload of image-heavy PDFs at 300 dpi: peak RSS drops from
about 1.1 GB to about 0.7 GB.
"""

from __future__ import annotations

import pymupdf


def release_caches() -> None:
    """Drop MuPDF's cached page resources. Safe to call at any point."""
    try:
        pymupdf.TOOLS.store_shrink(100)
    except Exception:  # noqa: BLE001 - only a cache; carry on without it
        pass
