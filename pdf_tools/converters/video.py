"""Video: a contact sheet of representative frames. Needs ffmpeg."""

from __future__ import annotations

import io

import pymupdf
from PIL import Image

from ..errors import ProcessingError
from ..externals import ffmpeg_still, find
from ..imaging import add_image_page
from .base import Context, Converter, Upload


class VideoConverter(Converter):
    name = "video"
    extensions = frozenset({
        ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm",
        ".mpg", ".mpeg", ".wmv", ".flv",
    })
    requires = ("ffmpeg",)

    def add_pages(self, doc: pymupdf.Document, upload: Upload, ctx: Context) -> None:
        png = ffmpeg_still(upload.data, upload.suffix, video=True)
        if png is None:
            if not find("ffmpeg"):
                raise ProcessingError(
                    f"{upload.name}: turning video into pages needs ffmpeg "
                    "installed on the server."
                )
            raise ProcessingError(f"{upload.name}: no video frames could be read.")
        ctx.note(f"{upload.name}: added as a frame contact sheet")
        with Image.open(io.BytesIO(png)) as im:
            im.load()
            add_image_page(doc, im, ctx.quality)
