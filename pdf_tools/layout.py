"""Page geometry: give every page the same paper size.

Converted pages are built at the target size already; PDFs that arrive as Letter,
A3, a photo-book square or anything else are rescaled here. Content is scaled to
fit, centred, and never stretched - so nothing is cropped and nothing is skewed.
"""

from __future__ import annotations

import pymupdf

import config

#: The target paper, portrait: (width, height) in points.
PORTRAIT: tuple[float, float] = tuple(pymupdf.paper_size(config.PAGE_SIZE))  # type: ignore[assignment]
if PORTRAIT[0] <= 0 or PORTRAIT[1] <= 0:  # unknown name -> PyMuPDF returns (-1, -1)
    PORTRAIT = tuple(pymupdf.paper_size("a4"))  # type: ignore[assignment]

LANDSCAPE: tuple[float, float] = (PORTRAIT[1], PORTRAIT[0])


def name() -> str:
    """The paper size in words, for notes shown to the user."""
    return config.PAGE_SIZE.upper()


def page_size(landscape: bool = False) -> tuple[float, float]:
    """Target page dimensions, sideways only if that is allowed."""
    return LANDSCAPE if (landscape and config.ALLOW_LANDSCAPE) else PORTRAIT


def size_for(width: float, height: float) -> tuple[float, float]:
    """The page to use for content of this shape."""
    return page_size(landscape=width > height)


def portrait_rect() -> pymupdf.Rect:
    return pymupdf.Rect(0, 0, *PORTRAIT)


def fit(content_w: float, content_h: float, page_w: float, page_h: float,
        margin: float = 0.0) -> pymupdf.Rect:
    """Largest centred rect inside the page that keeps the content's proportions."""
    box_w = max(page_w - 2 * margin, 1.0)
    box_h = max(page_h - 2 * margin, 1.0)
    scale = min(box_w / content_w, box_h / content_h)
    draw_w, draw_h = content_w * scale, content_h * scale
    x0 = margin + (box_w - draw_w) / 2
    y0 = margin + (box_h - draw_h) / 2
    return pymupdf.Rect(x0, y0, x0 + draw_w, y0 + draw_h)


def is_target_size(rect: pymupdf.Rect) -> bool:
    """True when a page already has the target dimensions."""
    tolerance = config.PAGE_SIZE_TOLERANCE
    for width, height in {PORTRAIT, page_size(landscape=True)}:
        if abs(rect.width - width) <= tolerance and abs(rect.height - height) <= tolerance:
            return True
    return False


def _remap(rect: pymupdf.Rect, source: pymupdf.Rect, target: pymupdf.Rect) -> pymupdf.Rect:
    """Move a rectangle from source-page space into the placed target rect."""
    scale = target.width / source.width
    return pymupdf.Rect(
        target.x0 + (rect.x0 - source.x0) * scale,
        target.y0 + (rect.y0 - source.y0) * scale,
        target.x0 + (rect.x1 - source.x0) * scale,
        target.y0 + (rect.y1 - source.y0) * scale,
    )


#: Heights used by the probe below; they must differ for the bug to show.
_PROBE_LINK_PAGE_HEIGHT = 800.0
_PROBE_DEST_PAGE_HEIGHT = 1000.0
_PROBE_DEST_Y = 200.0


def _merge_shifts_destinations() -> bool:
    """Does this PyMuPDF mis-convert GoTo destinations when merging documents?

    Up to at least 1.28, insert_pdf converts a jump destination using the height
    of the page the link sits on instead of the height of the page it points at,
    so the destination slides by the difference between the two. Documents whose
    pages are all the same height are unaffected, which is why the probe uses two
    different heights. Asking beats assuming: if a later release fixes this, the
    probe turns the workaround off by itself.
    """
    try:
        probe = pymupdf.open()
        probe.new_page(width=400, height=_PROBE_LINK_PAGE_HEIGHT)
        probe.new_page(width=400, height=_PROBE_DEST_PAGE_HEIGHT)
        probe[0].insert_link({
            "kind": pymupdf.LINK_GOTO,
            "from": pymupdf.Rect(10, 10, 90, 30),
            "page": 1,
            "to": pymupdf.Point(0, _PROBE_DEST_Y),
        })
        merged = pymupdf.open()
        merged.insert_pdf(probe)
        jumps = [x for x in merged[0].get_links() if x["kind"] == pymupdf.LINK_GOTO]
        landed = jumps[0]["to"].y if jumps else _PROBE_DEST_Y
        probe.close()
        merged.close()
        slid = _PROBE_DEST_Y - _PROBE_LINK_PAGE_HEIGHT + _PROBE_DEST_PAGE_HEIGHT
        return abs(landed - slid) < 2.0
    except Exception:  # noqa: BLE001 - never let a probe break startup
        return False


MERGE_SHIFTS_DESTINATIONS = _merge_shifts_destinations()


def repair_destinations(doc: pymupdf.Document) -> int:
    """Undo the jump-destination shift that merging introduces.

    Runs on the freshly merged document, before any resizing, so both resized and
    untouched pages end up with links pointing where they originally did.
    """
    if not MERGE_SHIFTS_DESTINATIONS:
        return 0
    fixed = 0
    heights = [page.rect.height for page in doc]
    for page in doc:
        for link in page.get_links():
            point = link.get("to")
            page_no = link.get("page", -1)
            if (
                link.get("kind") != pymupdf.LINK_GOTO
                or point is None
                or not 0 <= page_no < len(heights)
                or not link.get("xref")
            ):
                continue
            # Undo the wrong page's height, apply the right one.
            shift = heights[page.number] - heights[page_no]
            if not shift:
                continue
            corrected = dict(link)
            corrected["to"] = pymupdf.Point(point.x, point.y + shift)
            try:
                page.update_link(corrected)
                fixed += 1
            except Exception:  # noqa: BLE001 - a link is never worth failing the job
                continue
    return fixed


def _copy_links(
    src: pymupdf.Page,
    dst: pymupdf.Page,
    placement: list[tuple[pymupdf.Rect, pymupdf.Rect]],
) -> None:
    """Carry hyperlinks across, shifted to where their content now sits.

    show_pdf_page copies page content but not annotations, so links would
    otherwise be lost on any page that had to be resized. Both a link's `from`
    rectangle and its destination point are top-left based in PyMuPDF's API, so
    the same mapping serves for both.
    """
    source, target = placement[src.number]
    for link in src.get_links():
        box = link.get("from")
        if box is None:
            continue
        moved = dict(link)
        moved["from"] = _remap(box, source, target)
        # An internal jump lands on another page, which has its own placement.
        point = link.get("to")
        page_no = link.get("page", -1)
        if point is not None and 0 <= page_no < len(placement):
            dest_source, dest_target = placement[page_no]
            spot = _remap(
                pymupdf.Rect(point.x, point.y, point.x, point.y), dest_source, dest_target
            )
            moved["to"] = pymupdf.Point(spot.x0, spot.y0)
        try:
            dst.insert_link(moved)
        except Exception:  # noqa: BLE001 - a link is never worth failing the job
            continue


def normalize(doc: pymupdf.Document) -> tuple[pymupdf.Document | None, int]:
    """Rebuild `doc` with every page at the target size.

    Returns (new document, pages resized). The new document is None when every
    page already had the right size, so the common case copies nothing: pages our
    own converters produce are built at the target size to begin with.
    """
    off = [page.number for page in doc if not is_target_size(page.rect)]
    if not off:
        return None, 0

    out = pymupdf.open()
    placement: list[tuple[pymupdf.Rect, pymupdf.Rect]] = []
    for page in doc:
        source = page.rect
        page_w, page_h = size_for(source.width, source.height)
        target = fit(source.width, source.height, page_w, page_h, config.PDF_PAGE_MARGIN)
        placement.append((source, target))
        # show_pdf_page keeps vector art and selectable text as-is, honouring the
        # source page's own /Rotate.
        out.new_page(width=page_w, height=page_h).show_pdf_page(target, doc, page.number)

    for page in doc:
        _copy_links(page, out[page.number], placement)
    return out, len(off)
