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

#: Largest total upload accepted, in megabytes. Peak memory is a few times the
#: biggest single file, so keep this modest on a 1-2 GB Raspberry Pi.
MAX_UPLOAD_MB = _int("MAX_UPLOAD_MB", 500)
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

#: Point TEXT_FONT at any .ttf to render scripts the fonts below do not cover.
TEXT_FONT = _str("TEXT_FONT", "")
#: Searched in order for non-Latin text; the built-in Courier is used if none
#: exist. Conventional locations, not requirements.
UNICODE_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/consola.ttf",
)

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
# optional external tools
# --------------------------------------------------------------------------- #
#: Command names looked up on PATH. FFMPEG_BIN / SOFFICE_BIN override these with
#: an explicit path; no install location is ever hard-coded.
FFMPEG_NAMES = ("ffmpeg",)
SOFFICE_NAMES = ("soffice", "libreoffice")
FFMPEG_TIMEOUT = _int("FFMPEG_TIMEOUT", 120)
FFPROBE_TIMEOUT = _int("FFPROBE_TIMEOUT", 30)
SOFFICE_TIMEOUT = _int("SOFFICE_TIMEOUT", 180)

#: Video contact sheet grid, as columns x rows.
CONTACT_SHEET = (_int("CONTACT_SHEET_COLS", 3), _int("CONTACT_SHEET_ROWS", 3))
#: Width in pixels of each frame in the contact sheet.
CONTACT_SHEET_FRAME_WIDTH = _int("CONTACT_SHEET_FRAME_WIDTH", 480)
#: Clips shorter than this get a single frame instead of a grid.
CONTACT_SHEET_MIN_SECONDS = _float("CONTACT_SHEET_MIN_SECONDS", 2.0)
