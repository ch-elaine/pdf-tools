"""Photos and graphics: one image per page, fitted to A4."""

from __future__ import annotations

import pymupdf

from ..imaging import add_image_page, open_image, widest_useful_px
from .base import Context, Converter, Upload


class ImageConverter(Converter):
    name = "image"
    # Formats Pillow reads on its own.
    extensions = frozenset({
        ".png", ".jpg", ".jpeg", ".jpe", ".jfif", ".gif", ".bmp",
        ".tif", ".tiff", ".webp", ".ppm", ".pgm", ".tga", ".ico",
    })

    def add_pages(self, doc: pymupdf.Document, upload: Upload, ctx: Context) -> None:
        hint = widest_useful_px(ctx.quality)
        with open_image(upload.data, upload.name, upload.suffix, hint) as im:
            add_image_page(doc, im, ctx.quality, original=upload.data)


class CameraImageConverter(ImageConverter):
    """Modern phone/camera formats: Pillow may not read them, ffmpeg will."""

    name = "camera-image"
    extensions = frozenset({
        ".heic", ".heif", ".avif", ".jxl", ".jp2", ".j2k",
        ".dng", ".cr2", ".nef", ".arw",
    })
    requires = ("ffmpeg",)  # only when Pillow cannot decode the file itself
