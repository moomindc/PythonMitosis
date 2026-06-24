"""Tests for the saver module. All files are written to pytest's tmp_path."""
import pytest
from pathlib import Path
from PIL import Image

from mitosis.review import ReviewResult
from mitosis.saver import save_results, _ext_to_format, _ensure_compatible_mode


def _result(w=200, h=300, rotation=0, discarded=False, colour=(80, 120, 160)):
    return ReviewResult(
        image=Image.new("RGB", (w, h), colour),
        rotation=rotation,
        discarded=discarded,
    )


def _source(tmp_path: Path, name="scan.png") -> tuple:
    """Return (path_str, source_image) with a dummy PNG source file."""
    p = tmp_path / name
    img = Image.new("RGB", (10, 10), (240, 240, 240))
    img.save(p)
    img = Image.open(p)  # re-open so .format is set
    return str(p), img


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

def test_single_result_gets_a_suffix(tmp_path):
    src, src_img = _source(tmp_path)
    saved = save_results([_result()], src, src_img)
    assert len(saved) == 1
    assert saved[0].name == "scan_a.png"


def test_three_results_get_abc(tmp_path):
    src, src_img = _source(tmp_path)
    saved = save_results([_result(), _result(), _result()], src, src_img)
    names = [p.name for p in saved]
    assert names == ["scan_a.png", "scan_b.png", "scan_c.png"]


def test_discarded_consumes_letter(tmp_path):
    src, src_img = _source(tmp_path)
    results = [_result(), _result(discarded=True), _result()]
    saved = save_results(results, src, src_img)
    names = [p.name for p in saved]
    assert names == ["scan_a.png", "scan_c.png"]  # b is skipped, not renumbered


def test_all_discarded_returns_empty(tmp_path):
    src, src_img = _source(tmp_path)
    results = [_result(discarded=True), _result(discarded=True)]
    saved = save_results(results, src, src_img)
    assert saved == []


# ---------------------------------------------------------------------------
# Files actually written
# ---------------------------------------------------------------------------

def test_output_files_exist(tmp_path):
    src, src_img = _source(tmp_path)
    saved = save_results([_result(), _result()], src, src_img)
    for p in saved:
        assert p.exists()


def test_source_file_not_overwritten(tmp_path):
    src, src_img = _source(tmp_path, "scan.png")
    save_results([_result()], src, src_img)
    assert Path(src).exists()
    loaded = Image.open(src)
    assert loaded.size == (10, 10)  # still the original dummy image


# ---------------------------------------------------------------------------
# Rotation applied before save
# ---------------------------------------------------------------------------

def test_rotation_90_cw_swaps_dimensions(tmp_path):
    src, src_img = _source(tmp_path)
    saved = save_results([_result(w=100, h=200, rotation=90)], src, src_img)
    out = Image.open(saved[0])
    assert out.size == (200, 100)  # width/height swapped by 90° CW


def test_rotation_0_preserves_dimensions(tmp_path):
    src, src_img = _source(tmp_path)
    saved = save_results([_result(w=100, h=200, rotation=0)], src, src_img)
    out = Image.open(saved[0])
    assert out.size == (100, 200)


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------

def test_png_format_preserved(tmp_path):
    src, src_img = _source(tmp_path, "scan.png")
    saved = save_results([_result()], src, src_img)
    assert saved[0].suffix.lower() == ".png"
    assert Image.open(saved[0]).format == "PNG"


def test_jpeg_format_preserved(tmp_path):
    src = tmp_path / "scan.jpg"
    img = Image.new("RGB", (10, 10), (240, 240, 240))
    img.save(src, format="JPEG", quality=95)
    src_img = Image.open(src)
    saved = save_results([_result()], str(src), src_img)
    assert saved[0].suffix.lower() == ".jpg"
    assert Image.open(saved[0]).format == "JPEG"


# ---------------------------------------------------------------------------
# DPI preserved
# ---------------------------------------------------------------------------

def test_dpi_preserved(tmp_path):
    src = tmp_path / "scan.png"
    img = Image.new("RGB", (10, 10), (240, 240, 240))
    img.save(src, dpi=(300, 300))
    src_img = Image.open(src)

    saved = save_results([_result()], str(src), src_img)
    out = Image.open(saved[0])
    dpi = out.info.get("dpi")
    assert dpi is not None
    assert abs(dpi[0] - 300.0) < 1.0  # PNG round-trips via px/metre integers


# ---------------------------------------------------------------------------
# Mode compatibility
# ---------------------------------------------------------------------------

def test_rgba_converted_to_rgb_for_jpeg(tmp_path):
    img = Image.new("RGBA", (50, 50), (100, 150, 200, 128))
    result = _ensure_compatible_mode(img, "JPEG")
    assert result.mode == "RGB"


def test_rgb_unchanged_for_jpeg():
    img = Image.new("RGB", (50, 50))
    result = _ensure_compatible_mode(img, "JPEG")
    assert result.mode == "RGB"


def test_rgba_unchanged_for_png():
    img = Image.new("RGBA", (50, 50))
    result = _ensure_compatible_mode(img, "PNG")
    assert result.mode == "RGBA"


# ---------------------------------------------------------------------------
# _ext_to_format
# ---------------------------------------------------------------------------

def test_ext_to_format_cases():
    assert _ext_to_format(".jpg") == "JPEG"
    assert _ext_to_format(".jpeg") == "JPEG"
    assert _ext_to_format(".JPG") == "JPEG"
    assert _ext_to_format(".png") == "PNG"
    assert _ext_to_format(".tif") == "TIFF"
    assert _ext_to_format(".tiff") == "TIFF"
    assert _ext_to_format(".bmp") == "BMP"
    assert _ext_to_format(".unknown") == "PNG"  # safe default
