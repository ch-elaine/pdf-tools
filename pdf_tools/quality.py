"""The quality slider: a dpi figure, straight from the form.

The slider value is the dpi itself — no mapping, no presets. Images are never
kept at more than that many dots per inch for the size they occupy on the page.
JPEG quality is a fixed setting in config.py, since only dpi is on the slider.
"""

from __future__ import annotations

from dataclasses import dataclass

import config


@dataclass(frozen=True)
class Quality:
    """Encoder settings for one request."""

    target_dpi: int
    jpeg_quality: int = config.JPEG_QUALITY

    @property
    def value(self) -> int:
        """The slider position, which is the dpi."""
        return self.target_dpi

    @property
    def label(self) -> str:
        """Short word for this dpi, for notes and the page."""
        if self.target_dpi >= 300:
            return "print"
        if self.target_dpi >= 200:
            return "high"
        if self.target_dpi >= 120:
            return "good"
        if self.target_dpi >= 72:
            return "screen"
        return "draft"


def clamp(value: object) -> int:
    """Coerce anything the form sends into a dpi inside the slider's range."""
    try:
        dpi = int(round(float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return config.DPI_DEFAULT
    return max(config.DPI_MIN, min(config.DPI_MAX, dpi))


def resolve(value: object = None) -> Quality:
    """Build encoder settings from a slider position (a dpi)."""
    dpi = config.DPI_DEFAULT if value is None or value == "" else clamp(value)
    return Quality(target_dpi=dpi, jpeg_quality=config.JPEG_QUALITY)


#: Slider bounds handed to the template.
SLIDER = {
    "min": config.DPI_MIN,
    "max": config.DPI_MAX,
    "step": config.DPI_STEP,
    "default": clamp(config.DPI_DEFAULT),
}
