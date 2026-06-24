"""
Synthetic tests for the detector module.

All test images are generated programmatically so no real scan files are needed.
Documents are drawn as dark rectangles on a light background, matching the
typical closed-lid flatbed scanner output.
"""
import math
import numpy as np
import pytest
from PIL import Image, ImageDraw

from mitosis.detector import detect_documents, _rects_overlap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scan(
    width: int = 2000,
    height: int = 2800,
    background: tuple = (240, 240, 240),
) -> Image.Image:
    return Image.new("RGB", (width, height), background)


def _draw_rect(
    image: Image.Image,
    x: int,
    y: int,
    w: int,
    h: int,
    colour: tuple = (30, 30, 30),
    angle_deg: float = 0.0,
) -> None:
    """Draw a filled rectangle, optionally rotated about its centre."""
    draw = ImageDraw.Draw(image)
    if angle_deg == 0.0:
        draw.rectangle([x, y, x + w, y + h], fill=colour)
    else:
        cx, cy = x + w / 2, y + h / 2
        hw, hh = w / 2, h / 2
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        rotated = [
            (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)
            for dx, dy in corners
        ]
        draw.polygon(rotated, fill=colour)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_single_document_detected():
    scan = _make_scan()
    _draw_rect(scan, 400, 600, 1200, 1600)
    regions = detect_documents(scan, min_area_fraction=0.03)
    assert len(regions) == 1


def test_two_documents_detected():
    scan = _make_scan()
    _draw_rect(scan, 100, 200, 800, 1000)
    _draw_rect(scan, 1100, 200, 800, 1000)
    regions = detect_documents(scan, min_area_fraction=0.03)
    assert len(regions) == 2


def test_three_documents_detected():
    scan = _make_scan()
    _draw_rect(scan, 100, 100, 550, 700)
    _draw_rect(scan, 725, 100, 550, 700)
    _draw_rect(scan, 1350, 100, 550, 700)
    regions = detect_documents(scan, min_area_fraction=0.03)
    assert len(regions) == 3


def test_sort_order_left_to_right():
    scan = _make_scan()
    _draw_rect(scan, 1100, 200, 700, 900)  # right
    _draw_rect(scan, 100, 200, 700, 900)   # left
    regions = detect_documents(scan, min_area_fraction=0.03)
    assert len(regions) == 2
    assert regions[0].bounding_box[0] < regions[1].bounding_box[0]


def test_no_documents_raises():
    scan = _make_scan()
    with pytest.raises(ValueError, match="No documents detected"):
        detect_documents(scan, min_area_fraction=0.05)


def test_overlapping_documents_raises():
    # Use contrasting tones so Canny detects the interior edge where the two
    # documents meet — without that edge, they merge into one indistinct blob.
    scan = _make_scan()
    _draw_rect(scan, 100, 100, 1000, 1200, colour=(20, 20, 20))
    _draw_rect(scan, 500, 400, 1000, 1200, colour=(160, 160, 160))
    with pytest.raises(ValueError, match="overlap"):
        detect_documents(scan, min_area_fraction=0.03)


def test_small_artefact_ignored():
    """A tiny mark below the area threshold must not be returned as a document."""
    scan = _make_scan()
    _draw_rect(scan, 400, 600, 1200, 1600)   # real document
    _draw_rect(scan, 50, 50, 20, 20)          # tiny artefact
    regions = detect_documents(scan, min_area_fraction=0.03)
    assert len(regions) == 1


def test_skewed_document_detected():
    """A document rotated 15° should still be found."""
    scan = _make_scan()
    _draw_rect(scan, 500, 700, 900, 1200, angle_deg=15.0)
    regions = detect_documents(scan, min_area_fraction=0.03)
    assert len(regions) == 1


def test_bounding_box_plausible():
    scan = _make_scan(width=2000, height=2800)
    _draw_rect(scan, 400, 600, 1000, 1400)
    regions = detect_documents(scan, min_area_fraction=0.03)
    x, y, w, h = regions[0].bounding_box
    assert 300 <= x <= 500
    assert 500 <= y <= 700
    assert 900 <= w <= 1100
    assert 1300 <= h <= 1500


# ---------------------------------------------------------------------------
# Unit tests for internal helpers
# ---------------------------------------------------------------------------

def test_rects_no_overlap():
    assert not _rects_overlap((0, 0, 100, 100), (200, 0, 100, 100))


def test_rects_overlap():
    assert _rects_overlap((0, 0, 200, 200), (100, 100, 200, 200))


def test_rects_touching_edge_not_overlap():
    # Touching exactly on an edge is not considered overlapping
    assert not _rects_overlap((0, 0, 100, 100), (100, 0, 100, 100))
