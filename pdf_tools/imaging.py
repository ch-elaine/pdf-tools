"""Shared bitmap helpers: decode anything, and place it on a page."""

from __future__ import annotations

import io

import pymupdf
from PIL import Image, ImageOps

import config

from .errors import ProcessingError
from .externals import ffmpeg_still, find
from .layout import PORTRAIT, fit, size_for
from .quality import Quality

Image.MAX_IMAGE_PIXELS = config.MAX_IMAGE_PIXELS


def flatten(im: Image.Image) -> Image.Image:
    """Drop alpha onto white and land on a JPEG-compatible mode."""
    im = ImageOps.exif_transpose(im) or im
    if im.mode == "P":
        im = im.convert("RGBA" if "transparency" in im.info else "RGB")
    if im.mode in ("RGBA", "LA"):
        rgba = im.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if im.mode in ("L", "1", "I;16", "I"):
        return im.convert("L")
    if im.mode != "RGB":
        return im.convert("RGB")
    return im


def to_jpeg(im: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def widest_useful_px(quality: Quality) -> int:
    """Most pixels across that any page can actually show at this dpi.

    Used as a decode hint: a 40 megapixel photo never needs to be unpacked in
    full just to be shrunk, and the full-size bitmap is the largest single thing
    in memory while a page is being built.
    """
    longest = max(*PORTRAIT) - 2 * config.IMAGE_MARGIN
    return max(1, int(quality.target_dpi * longest / 72))


def open_image(
    blob: bytes, name: str, suffix: str, hint_px: int | None = None
) -> Image.Image:
    """Decode with Pillow, falling back to ffmpeg for formats it cannot read.

    `hint_px` lets JPEGs decode straight to a smaller size (Pillow's draft mode
    uses the JPEG scaling factors), which costs a fraction of the memory and time.
    It never decodes smaller than the hint, so quality is unaffected.
    """
    try:
        im = Image.open(io.BytesIO(blob))
        if hint_px:
            im.draft(None, (hint_px, hint_px))
        im.load()
        return im
    except Exception as exc:  # noqa: BLE001 - try the heavier decoder before giving up
        png = ffmpeg_still(blob, suffix, video=False)
        if png is None:
            hint = "" if find("ffmpeg") else " Install ffmpeg for HEIC/AVIF/RAW support."
            raise ProcessingError(f"Could not read image {name}.{hint}") from exc
        im = Image.open(io.BytesIO(png))
        im.load()
        return im


def add_image_page(
    doc: pymupdf.Document,
    im: Image.Image,
    quality: Quality,
    original: bytes | None = None,
) -> None:
    """Add one page holding `im`, fitted to the page and capped at the target dpi."""
    # Read before flatten(), which applies and then strips EXIF orientation.
    upright = im.getexif().get(0x0112, 1) in (0, 1)
    reusable = original is not None and upright and im.mode in ("RGB", "L")

    im = flatten(im)

    page_w, page_h = size_for(im.width, im.height)
    rect = fit(im.width, im.height, page_w, page_h, config.IMAGE_MARGIN)

    # Never carry more pixels than the chosen dpi can show at that size.
    max_px = max(1, int(quality.target_dpi * rect.width / 72))
    downsampled = im.width > max_px
    if downsampled:
        im = im.resize((max_px, max(1, round(im.height * max_px / im.width))), Image.LANCZOS)

    payload = to_jpeg(im, quality.jpeg_quality)
    if (
        reusable
        and not downsampled
        and original[:2] == b"\xff\xd8"  # already a JPEG, embeddable as-is
        and len(original) <= len(payload)
    ):
        payload = original  # re-encoding would only cost quality and bytes

    page = doc.new_page(width=page_w, height=page_h)
    page.insert_image(rect, stream=payload)
