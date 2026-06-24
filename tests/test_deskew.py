"""
Integration tests for the deskew module.

Each test draws a synthetic document on a scan, runs the detector to get
regions, then deskews and verifies the output.
"""
import math
import numpy as np
import pytest
from PIL import Image, ImageDraw

from mitosis.detector import detect_documents
from mitosis.deskew import deskew_regions


MIN_AREA = 0.03


def _make_scan(width=2000, height=2800, bg=(240, 240, 240), mode="RGB"):
    return Image.new(mode, (width, height), bg)


def _draw_rect(image, x, y, w, h, colour=(30, 30, 30), angle_deg=0.0):
    draw = ImageDraw.Draw(image)
    if angle_deg == 0.0:
        draw.rectangle([x, y, x + w, y + h], fill=colour)
    else:
        cx, cy = x + w / 2, y + h / 2
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        corners = [
            (cx + (dx * cos_a - dy * sin_a), cy + (dx * sin_a + dy * cos_a))
            for dx, dy in [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]
        ]
        draw.polygon(corners, fill=colour)


def _detect_and_deskew(scan):
    regions = detect_documents(scan, min_area_fraction=MIN_AREA)
    return deskew_regions(scan, regions)


# ---------------------------------------------------------------------------
# Basic extraction
# ---------------------------------------------------------------------------

def test_single_landscape_document():
    scan = _make_scan()
    _draw_rect(scan, 300, 600, 1400, 900)  # landscape 1400×900
    results = _detect_and_deskew(scan)
    assert len(results) == 1
    w, h = results[0].size
    assert 1300 <= w <= 1500
    assert 800 <= h <= 1000


def test_single_portrait_document():
    scan = _make_scan()
    _draw_rect(scan, 500, 200, 800, 1800)  # portrait 800×1800
    results = _detect_and_deskew(scan)
    assert len(results) == 1
    w, h = results[0].size
    # After deskew the longer side becomes h (portrait orientation)
    assert min(w, h) <= 900
    assert max(w, h) >= 1700


def test_two_documents_both_extracted():
    scan = _make_scan()
    _draw_rect(scan, 100, 300, 800, 1000)
    _draw_rect(scan, 1100, 300, 800, 1000)
    results = _detect_and_deskew(scan)
    assert len(results) == 2


# ---------------------------------------------------------------------------
# Deskewing correctness
# ---------------------------------------------------------------------------

def test_small_tilt_corrected():
    """A 7° tilt should produce output with dimensions close to the original."""
    scan = _make_scan()
    _draw_rect(scan, 400, 500, 1000, 700, angle_deg=7.0)
    results = _detect_and_deskew(scan)
    assert len(results) == 1
    w, h = results[0].size
    # Tilt of 7° changes apparent size only slightly
    assert 900 <= w <= 1100
    assert 600 <= h <= 800


def test_45_degree_tilt():
    """A document at exactly 45° is a degenerate case; it should still extract."""
    scan = _make_scan()
    _draw_rect(scan, 600, 600, 800, 800, angle_deg=45.0)  # square, so 45° is symmetric
    results = _detect_and_deskew(scan)
    assert len(results) == 1
    w, h = results[0].size
    assert 700 <= w <= 900
    assert 700 <= h <= 900


def test_negative_tilt():
    """Tilt in the other direction should also be corrected."""
    scan = _make_scan()
    _draw_rect(scan, 400, 500, 1000, 700, angle_deg=-7.0)
    results = _detect_and_deskew(scan)
    assert len(results) == 1
    w, h = results[0].size
    assert 900 <= w <= 1100
    assert 600 <= h <= 800


# ---------------------------------------------------------------------------
# Output properties
# ---------------------------------------------------------------------------

def test_output_is_pil_image():
    scan = _make_scan()
    _draw_rect(scan, 300, 400, 1000, 700)
    results = _detect_and_deskew(scan)
    assert isinstance(results[0], Image.Image)


def test_rgb_mode_preserved():
    scan = _make_scan(mode="RGB")
    _draw_rect(scan, 300, 400, 1000, 700)
    results = _detect_and_deskew(scan)
    assert results[0].mode == "RGB"


def test_grayscale_mode_preserved():
    scan = _make_scan(mode="L", bg=240)
    draw = ImageDraw.Draw(scan)
    draw.rectangle([300, 400, 1300, 1100], fill=30)
    regions = detect_documents(scan, min_area_fraction=MIN_AREA)
    results = deskew_regions(scan, regions)
    assert results[0].mode == "L"


def test_output_pixels_not_all_background():
    """The extracted crop must contain document pixels, not just scanner background."""
    scan = _make_scan(bg=(240, 240, 240))
    _draw_rect(scan, 400, 500, 1000, 700, colour=(20, 20, 20))
    results = _detect_and_deskew(scan)
    arr = np.array(results[0])
    dark_pixels = np.sum(arr < 100)
    assert dark_pixels > 0, "Extracted image contains no document pixels"
