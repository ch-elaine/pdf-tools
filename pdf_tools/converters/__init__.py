"""Registry of format modules.

To support a new format: add a module here with a Converter subclass, then list
it in REGISTRY. The pipeline picks converters purely by file extension.
"""

from __future__ import annotations

from .base import Context, Converter, Upload
from .html import HtmlConverter
from .image import CameraImageConverter, ImageConverter
from .pdf_doc import PdfConverter
from .text import TextConverter
from .video import VideoConverter

REGISTRY: tuple[Converter, ...] = (
    PdfConverter(),
    ImageConverter(),
    CameraImageConverter(),
    TextConverter(),
    HtmlConverter(),
    VideoConverter(),
)


def _index() -> dict[str, Converter]:
    table: dict[str, Converter] = {}
    for converter in REGISTRY:
        for ext in converter.extensions:
            if ext in table:
                raise RuntimeError(
                    f"{ext} is claimed by both {table[ext].name} and {converter.name}"
                )
            table[ext] = converter
    return table


BY_EXTENSION = _index()


def for_suffix(suffix: str) -> Converter | None:
    return BY_EXTENSION.get(suffix.lower())


def supported_extensions() -> set[str]:
    return set(BY_EXTENSION)


__all__ = [
    "BY_EXTENSION",
    "Context",
    "Converter",
    "REGISTRY",
    "Upload",
    "for_suffix",
    "supported_extensions",
]
