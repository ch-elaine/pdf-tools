"""Every tunable setting for pdf-tools, in one place.

Edit the values here, or override any of them with an environment variable of the
same name — handy for running the same checkout with different limits:

    MAX_UPLOAD_MB=100 PORT=8080 python app.py

Run from the project directory (or `gunicorn --chdir /path/to/pdf-tools`) so this
module is importable.
"""

from __future__ import annotations

import os

TRUTHY = {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in TRUTHY


def _str(name: str, default: str) -> str:
    return os.environ.get(name, default)


# --------------------------------------------------------------------------- #
# web server
# --------------------------------------------------------------------------- #
HOST = _str("HOST", "127.0.0.1")
PORT = _int("PORT", 5000)
DEBUG = _bool("DEBUG", False)

#: Largest total upload accepted, in megabytes.
#:
#: This is the memory dial. Measured worst case - image-heavy PDFs, all different,
#: at 300 dpi - peaks at roughly 250 MB + 3 MB per MB uploaded, so 120 MB of
#: uploads peaks near 700 MB and stays inside a 1 GB budget. Ordinary uploads at
#: the default dpi use about half that. Raise it only with more RAM, and remember
#: each concurrent request pays the cost again: on a 1 GB machine, run one worker.
MAX_UPLOAD_MB = _int("MAX_UPLOAD_MB", 120)
#: Most files accepted in one submission.
MAX_FILES = _int("MAX_FILES", 100)

# --------------------------------------------------------------------------- #
# quality slider - the value IS the dpi
# --------------------------------------------------------------------------- #
#: The slider is a plain dpi figure: no image is kept at more than this many dots
#: per inch for the size it is shown at on the page. Higher means more detail and
#: a bigger file. 300 is print quality, 150 is comfortable, 72 is screen-only.
DPI_MIN = _int("DPI_MIN", 10)
DPI_MAX = _int("DPI_MAX", 300)
DPI_STEP = _int("DPI_STEP", 5)
DPI_DEFAULT = _int("DPI_DEFAULT", 100)

#: JPEG quality used whenever an image is re-encoded. Not on the slider: 80 is
#: the usual sweet spot where artefacts stay invisible at normal viewing size.
JPEG_QUALITY = _int("JPEG_QUALITY", 80)

# --------------------------------------------------------------------------- #
# page geometry
# --------------------------------------------------------------------------- #
#: Any name PyMuPDF knows: "a4", "letter", "a5", "legal", ...
PAGE_SIZE = _str("PAGE_SIZE", "a4")
#: Give wider-than-tall pages and images the page turned sideways (still A4
#: paper). Set false to force every page upright.
ALLOW_LANDSCAPE = _bool("ALLOW_LANDSCAPE", True)
#: White space around a placed image, in points (72 pt = 1 inch).
IMAGE_MARGIN = _float("IMAGE_MARGIN", 18.0)
#: How far a resized PDF page is inset from the paper edge, in points.
PDF_PAGE_MARGIN = _float("PDF_PAGE_MARGIN", 0.0)
#: A page within this many points of the target size counts as already correct.
PAGE_SIZE_TOLERANCE = _float("PAGE_SIZE_TOLERANCE", 1.0)

# --------------------------------------------------------------------------- #
# text pages
# --------------------------------------------------------------------------- #
TEXT_MARGIN = _float("TEXT_MARGIN", 54.0)
TEXT_FONT_SIZE = _float("TEXT_FONT_SIZE", 9.0)
TEXT_LINE_HEIGHT = _float("TEXT_LINE_HEIGHT", 1.35)
TEXT_TAB_WIDTH = _int("TEXT_TAB_WIDTH", 4)

#: Base-14 font for plain Latin text. Never embedded, so those PDFs stay tiny.
TEXT_BASE_FONT = _str("TEXT_BASE_FONT", "cour")
#: Wide-coverage font embedded when Courier cannot render the text. Comes from
#: the pymupdf-fonts package: monospaced, covers Greek, Cyrillic, Arabic, Hebrew.
TEXT_UNICODE_FONT = _str("TEXT_UNICODE_FONT", "cascadia")
#: Optional path to your own .ttf, used ahead of the packaged font - the way in
#: for scripts Cascadia lacks, such as Chinese, Japanese or Korean.
TEXT_FONT = _str("TEXT_FONT", "")

#: Safety valve for a runaway HTML layout.
HTML_MAX_PAGES = _int("HTML_MAX_PAGES", 2000)

# --------------------------------------------------------------------------- #
# compression
# --------------------------------------------------------------------------- #
#: Images smaller than this are never worth re-encoding (icons, logos, rules).
MIN_IMAGE_BYTES = _int("MIN_IMAGE_BYTES", 8 * 1024)
#: Only swap in a re-encoded image if it saves at least this fraction.
MIN_IMAGE_GAIN = _float("MIN_IMAGE_GAIN", 0.10)
#: Decompression-bomb guard for incoming bitmaps.
MAX_IMAGE_PIXELS = _int("MAX_IMAGE_PIXELS", 500_000_000)

# --------------------------------------------------------------------------- #
# ffmpeg: the only optional external tool
# --------------------------------------------------------------------------- #
#: Command names looked up on PATH. FFMPEG_BIN overrides this with an explicit
#: path; no install location is ever hard-coded.
FFMPEG_NAMES = ("ffmpeg",)
FFMPEG_TIMEOUT = _int("FFMPEG_TIMEOUT", 120)
FFPROBE_TIMEOUT = _int("FFPROBE_TIMEOUT", 30)

#: Video contact sheet grid, as columns x rows.
CONTACT_SHEET = (_int("CONTACT_SHEET_COLS", 3), _int("CONTACT_SHEET_ROWS", 3))
#: Width in pixels of each frame in the contact sheet.
CONTACT_SHEET_FRAME_WIDTH = _int("CONTACT_SHEET_FRAME_WIDTH", 480)
#: Clips shorter than this get a single frame instead of a grid.
CONTACT_SHEET_MIN_SECONDS = _float("CONTACT_SHEET_MIN_SECONDS", 2.0)
