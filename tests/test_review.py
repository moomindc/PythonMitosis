"""Tests for the review module. No display window is opened — all tests
inject a key sequence so cv2.imshow/waitKey are bypassed entirely."""
import pytest
from PIL import Image

from mitosis.review import (
    review_interactive,
    rotate_pil,
    _scale_to_fit,
    KEY_LEFT, KEY_RIGHT, KEY_ESC, KEY_ENTER, KEY_DISCARD,
)


def _img(w=200, h=300, colour=(100, 150, 200)):
    return Image.new("RGB", (w, h), colour)


# ---------------------------------------------------------------------------
# rotate_pil
# ---------------------------------------------------------------------------

def test_rotate_0_returns_same_dimensions():
    img = _img(200, 300)
    out = rotate_pil(img, 0)
    assert out.size == (200, 300)


def test_rotate_90_cw_swaps_dimensions():
    img = _img(200, 300)
    out = rotate_pil(img, 90)
    assert out.size == (300, 200)


def test_rotate_180_preserves_dimensions():
    img = _img(200, 300)
    out = rotate_pil(img, 180)
    assert out.size == (200, 300)


def test_rotate_270_cw_swaps_dimensions():
    img = _img(200, 300)
    out = rotate_pil(img, 270)
    assert out.size == (300, 200)


def test_rotate_360_same_as_0():
    img = _img(200, 300)
    assert rotate_pil(img, 360).size == rotate_pil(img, 0).size


def test_rotate_90_pixel_correctness():
    """Top-left pixel of original should become top-right after 90° CW."""
    img = Image.new("RGB", (4, 4), (0, 0, 0))
    img.putpixel((0, 0), (255, 0, 0))  # top-left = red
    out = rotate_pil(img, 90)
    assert out.getpixel((3, 0)) == (255, 0, 0)  # should appear at top-right


# ---------------------------------------------------------------------------
# _scale_to_fit
# ---------------------------------------------------------------------------

def test_scale_large_image_fits_within_max():
    img = _img(2000, 1500)
    out = _scale_to_fit(img, 900)
    assert max(out.size) <= 900


def test_scale_small_image_not_upscaled():
    img = _img(100, 80)
    out = _scale_to_fit(img, 900)
    assert out.size == (100, 80)


def test_scale_aspect_ratio_preserved():
    img = _img(2000, 1000)
    out = _scale_to_fit(img, 900)
    w, h = out.size
    assert abs(w / h - 2.0) < 0.02


# ---------------------------------------------------------------------------
# review_interactive (headless via _key_sequence)
# ---------------------------------------------------------------------------

def test_confirm_single_image_no_rotation():
    results = review_interactive([_img()], _key_sequence=[KEY_ENTER[0]])
    assert len(results) == 1
    assert results[0].rotation == 0
    assert not results[0].discarded


def test_rotate_right_then_confirm():
    keys = [KEY_RIGHT[0], KEY_ENTER[0]]
    results = review_interactive([_img()], _key_sequence=keys)
    assert results[0].rotation == 90


def test_rotate_left_then_confirm():
    keys = [KEY_LEFT[0], KEY_ENTER[0]]
    results = review_interactive([_img()], _key_sequence=keys)
    assert results[0].rotation == 270


def test_rotate_accumulates():
    keys = [KEY_RIGHT[0], KEY_RIGHT[0], KEY_RIGHT[0], KEY_ENTER[0]]
    results = review_interactive([_img()], _key_sequence=keys)
    assert results[0].rotation == 270


def test_discard():
    results = review_interactive([_img()], _key_sequence=[KEY_DISCARD[0]])
    assert results[0].discarded
    assert results[0].rotation == 0


def test_esc_raises_system_exit():
    with pytest.raises(SystemExit):
        review_interactive([_img()], _key_sequence=[KEY_ESC])


def test_multiple_images_independent_rotations():
    keys = [
        KEY_RIGHT[0], KEY_ENTER[0],   # image 1: rotate right, confirm
        KEY_ENTER[0],                  # image 2: confirm as-is
    ]
    results = review_interactive([_img(), _img()], _key_sequence=keys)
    assert results[0].rotation == 90
    assert results[1].rotation == 0


def test_multiple_images_one_discarded():
    keys = [
        KEY_ENTER[0],       # image 1: confirm
        KEY_DISCARD[0],     # image 2: discard
        KEY_ENTER[0],       # image 3: confirm
    ]
    results = review_interactive([_img(), _img(), _img()], _key_sequence=keys)
    assert not results[0].discarded
    assert results[1].discarded
    assert not results[2].discarded


def test_space_also_confirms():
    results = review_interactive([_img()], _key_sequence=[KEY_ENTER[1]])  # space
    assert not results[0].discarded
    assert results[0].rotation == 0


def test_uppercase_d_also_discards():
    results = review_interactive([_img()], _key_sequence=[KEY_DISCARD[1]])
    assert results[0].discarded
