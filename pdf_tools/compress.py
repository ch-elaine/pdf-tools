"""Make a finished PDF smaller without visibly hurting it."""

from __future__ import annotations

import io

import pymupdf
from PIL import Image

import config

from .imaging import flatten, to_jpeg
from .quality import Quality

#: Keep a re-encode only if it saves at least this fraction of the bytes.
KEEP_BELOW = 1.0 - config.MIN_IMAGE_GAIN

_SAVE_KWARGS = {
    "garbage": 4,
    "deflate": True,
    "deflate_images": True,
    "deflate_fonts": True,
    "clean": True,
    "use_objstms": 1,
}


def save(doc: pymupdf.Document) -> bytes:
    """Serialise with every space saving this PyMuPDF build supports."""
    kwargs = dict(_SAVE_KWARGS)
    while True:
        try:
            return doc.tobytes(**kwargs)
        except TypeError:
            if not kwargs:
                raise
            kwargs.pop(next(reversed(kwargs)))  # drop newest option, retry
        except ValueError:
            # Encrypted/linearised edge cases: fall back to a plain save.
            return doc.tobytes()


def shrink_images(doc: pymupdf.Document, quality: Quality) -> int:
    """Downsample and re-encode images that carry more detail than they show."""
    replaced = 0
    seen: set[int] = set()
    for page in doc:
        try:
            images = page.get_images(full=True)
        except Exception:  # noqa: BLE001
            continue
        for info in images:
            xref, smask = info[0], info[1]
            if xref in seen:
                continue
            seen.add(xref)
            if smask:
                continue  # replacing a masked image would drop its transparency
            try:
                rects = page.get_image_rects(xref)
            except Exception:  # noqa: BLE001
                rects = []
            if rects:
                shown_w = max(r.width for r in rects)
                shown_h = max(r.height for r in rects)
            else:
                # Images nested in a Form XObject - which is how resized pages
                # hold their content - report no placement. Assume they fill the
                # page: correct for full-page scans, and for anything smaller it
                # under-estimates the dpi, so detail is kept rather than lost.
                shown_w, shown_h = page.rect.width, page.rect.height
            if shown_w <= 1 or shown_h <= 1:
                continue
            try:
                raw = doc.extract_image(xref)
            except Exception:  # noqa: BLE001
                continue
            data = raw.get("image") if raw else None
            if not data or len(data) < config.MIN_IMAGE_BYTES:
                continue
            width, height = raw.get("width", 0), raw.get("height", 0)
            if width < 2 or height < 2:
                continue

            dpi = max(width / (shown_w / 72), height / (shown_h / 72))
            scale = min(1.0, quality.target_dpi / dpi) if dpi > 0 else 1.0
            try:
                with Image.open(io.BytesIO(data)) as im:
                    im.load()
                    if im.mode == "1":
                        continue  # bitonal scans beat any JPEG already
                    if scale < 1.0:
                        im = im.resize(
                            (max(1, int(width * scale)), max(1, int(height * scale))),
                            Image.LANCZOS,
                        )
                    candidate = to_jpeg(flatten(im), quality.jpeg_quality)
            except Exception:  # noqa: BLE001 - unsupported codec (JBIG2, JPX, ...)
                continue

            if len(candidate) < len(data) * KEEP_BELOW:
                try:
                    page.replace_image(xref, stream=candidate)
                    replaced += 1
                except Exception:  # noqa: BLE001
                    continue
    return replaced


def compress(merged: bytes, quality: Quality, notes: list[str]) -> bytes:
    """Shrink `merged` further, keeping the result only if it really got smaller.

    Saving with garbage collection renumbers objects, so the image pass runs on a
    freshly opened copy: a document must be mutated first and saved once, or the
    rewritten xref table leaves replaced images pointing at dead objects.
    """
    with pymupdf.open(stream=merged, filetype="pdf") as doc:
        replaced = shrink_images(doc, quality)
        try:
            doc.subset_fonts(verbose=False)
        except Exception:  # noqa: BLE001 - optional, and version dependent
            pass
        shrunk = save(doc)

    if replaced and len(shrunk) < len(merged):
        notes.append(f"{replaced} image(s) downsampled to {quality.target_dpi} dpi")
        return shrunk
    return merged if len(merged) <= len(shrunk) else shrunk
