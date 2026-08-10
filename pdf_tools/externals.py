"""Optional command-line helpers.

Nothing here is required for the core pipeline (PDFs, images, text, HTML). Tools
are always resolved through PATH — never a hard-coded install location — so the
same code works on a Raspberry Pi, a container or a laptop. Each tool may also
be pointed at explicitly with an environment variable, e.g. FFMPEG_BIN.

Command names, timeouts and the contact-sheet grid all come from config.py.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import config

from .errors import ProcessingError

# tool name -> (command names to try on PATH, what it buys you)
OPTIONAL_TOOLS: dict[str, tuple[tuple[str, ...], str]] = {
    "ffmpeg": (config.FFMPEG_NAMES, "HEIC/AVIF/RAW photos and video frames"),
    "soffice": (config.SOFFICE_NAMES, "Word/Excel/PowerPoint documents"),
}


def find(tool: str) -> str | None:
    """Locate an optional tool, or return None if it is not installed."""
    names, _ = OPTIONAL_TOOLS.get(tool, ((tool,), ""))
    override = os.environ.get(f"{tool.upper()}_BIN")
    if override:
        return override if shutil.which(override) else None
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def available() -> dict[str, str | None]:
    """Which optional tools this host has — handy for diagnostics."""
    return {tool: find(tool) for tool in OPTIONAL_TOOLS}


def run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ProcessingError(f"{Path(cmd[0]).name} timed out after {timeout}s.") from exc
    except OSError as exc:
        raise ProcessingError(f"Could not run {Path(cmd[0]).name}: {exc}") from exc


def _ffprobe(ffmpeg: str) -> str | None:
    """ffprobe ships with ffmpeg; look on PATH, then beside the ffmpeg we found."""
    found = shutil.which("ffprobe")
    if found:
        return found
    sibling = Path(ffmpeg).with_name("ffprobe")
    return str(sibling) if sibling.is_file() else None


def _duration(ffmpeg: str, path: Path) -> float | None:
    """Length of a clip in seconds, or None if it cannot be determined."""
    ffprobe = _ffprobe(ffmpeg)
    if not ffprobe:
        return None
    result = run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        config.FFPROBE_TIMEOUT,
    )
    try:
        seconds = float(result.stdout.decode("utf-8", "replace").strip())
    except ValueError:
        return None
    return seconds if seconds > 0 else None


def _sheet_filters(ffmpeg: str, src: Path) -> list[str]:
    """Filter chains to try for a video, best first.

    A clip is sampled evenly across its whole length so the sheet actually
    summarises it; `thumbnail` alone samples only the opening seconds and leaves
    most of the grid empty.
    """
    cols, rows = config.CONTACT_SHEET
    cells = max(1, cols * rows)
    width = config.CONTACT_SHEET_FRAME_WIDTH
    grid = f"tile={cols}x{rows}:margin=6:padding=6:color=white"

    chains = []
    duration = _duration(ffmpeg, src)
    if duration and duration >= config.CONTACT_SHEET_MIN_SECONDS:
        # Spread `cells` samples over the whole clip, keeping a sane lower bound.
        fps = max(cells / duration, 0.02)
        chains.append(
            f"fps={fps:.5f},scale={width}:-2:force_original_aspect_ratio=decrease,{grid}"
        )
    chains.append(f"thumbnail={max(2, cells)},scale={width}:-2,{grid}")
    return chains


def ffmpeg_still(blob: bytes, suffix: str, *, video: bool) -> bytes | None:
    """Render a still PNG from anything ffmpeg understands.

    Video becomes a contact sheet of frames sampled across the clip, so it turns
    into something meaningful on paper. Returns None when ffmpeg is missing or
    cannot decode the input.
    """
    ffmpeg = find("ffmpeg")
    if not ffmpeg:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"input{suffix or '.bin'}"
        src.write_bytes(blob)
        out = Path(tmp) / "out.png"
        base = [ffmpeg, "-v", "error", "-nostdin", "-y", "-i", str(src), "-an", "-sn"]

        attempts = [
            [*base, "-vf", chain, "-frames:v", "1", str(out)]
            for chain in (_sheet_filters(ffmpeg, src) if video else [])
        ]
        attempts.append([*base, "-frames:v", "1", str(out)])  # plain single frame

        for cmd in attempts:
            result = run(cmd, config.FFMPEG_TIMEOUT)
            if result.returncode == 0 and out.exists() and out.stat().st_size:
                return out.read_bytes()
            out.unlink(missing_ok=True)
    return None
