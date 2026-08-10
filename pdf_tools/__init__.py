"""pdf-tools: merge any pile of uploads into one compressed PDF.

Public API used by the web layer:

    build_pdf(files, dpi) -> Result
    dpi_slider()          -> bounds for the form control
    supported_extensions()
    ProcessingError

Settings live in config.py at the project root.
"""

from .converters import supported_extensions
from .errors import ProcessingError
from .externals import available as external_tools
from .pipeline import Result, build_pdf
from .quality import SLIDER, Quality, resolve as resolve_quality


def dpi_slider() -> dict[str, int]:
    """Min/max/step/default for the dpi slider on the page."""
    return dict(SLIDER)


__all__ = [
    "ProcessingError",
    "Quality",
    "Result",
    "build_pdf",
    "external_tools",
    "dpi_slider",
    "resolve_quality",
    "supported_extensions",
]
