"""The contract every format module implements.

A converter takes one upload and appends pages to the document being built. It
never saves, never compresses and never sees the other uploads - the pipeline
owns all of that. Adding support for a new format means adding one module here
and listing it in `converters/__init__.py`; nothing else changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pymupdf

from ..quality import Quality


@dataclass(frozen=True)
class Upload:
    name: str
    data: bytes
    suffix: str  # lower-cased extension, including the dot


@dataclass
class Context:
    """Per-request state shared with every converter."""

    quality: Quality
    notes: list[str] = field(default_factory=list)

    def note(self, message: str) -> None:
        """Record something the user should know about their file."""
        self.notes.append(message)


class Converter:
    """Base class: subclasses declare what they accept and add pages."""

    name: str = ""
    extensions: frozenset[str] = frozenset()
    # Optional command-line tools this converter needs (see externals.py).
    requires: tuple[str, ...] = ()

    def add_pages(self, doc: pymupdf.Document, upload: Upload, ctx: Context) -> None:
        raise NotImplementedError
