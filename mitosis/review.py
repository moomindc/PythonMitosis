import cv2
import numpy as np
from dataclasses import dataclass
from typing import Iterator, List, Optional
from PIL import Image


# ---------------------------------------------------------------------------
# Key code constants — exposed so tests can inject them without magic numbers
# ---------------------------------------------------------------------------
KEY_ESC = 27
KEY_ENTER = (13, 32)                    # Enter, Space
KEY_DISCARD = (ord('d'), ord('D'))
KEY_LEFT = (2424832, 65361)             # left arrow: Windows, Linux/Mac
KEY_RIGHT = (2555904, 65363)            # right arrow: Windows, Linux/Mac

_MAX_PREVIEW = 900                      # longest side of the preview window (px)
_WINDOW = "Mitosis"


@dataclass
class ReviewResult:
    image: Image.Image  # deskewed PIL image at full resolution
    rotation: int       # degrees clockwise: 0, 90, 180, or 270
    discarded: bool


def review_interactive(
    images: List[Image.Image],
    _key_sequence: Optional[List[int]] = None,
) -> List[ReviewResult]:
    """
    Show each deskewed image for orientation confirmation.

    Controls: left/right arrows rotate 90°, D discards, Enter/Space confirms,
    Esc aborts the entire run (no files written).

    Pass _key_sequence in tests to drive the loop without a display window.
    Returns one ReviewResult per image, including discarded ones.
    """
    results: List[ReviewResult] = []
    total = len(images)
    key_iter: Optional[Iterator[int]] = iter(_key_sequence) if _key_sequence is not None else None

    for idx, image in enumerate(images):
        rotation = 0
        discarded = False

        while True:
            if key_iter is None:
                preview = _make_preview(image, rotation, idx + 1, total)
                cv2.imshow(_WINDOW, preview)
                key = cv2.waitKeyEx(0)
            else:
                key = next(key_iter)

            action = _handle_key(key)

            if action == "abort":
                if key_iter is None:
                    cv2.destroyAllWindows()
                raise SystemExit(0)
            elif action == "rotate_ccw":
                rotation = (rotation - 90) % 360
            elif action == "rotate_cw":
                rotation = (rotation + 90) % 360
            elif action == "discard":
                discarded = True
                break
            elif action == "confirm":
                break

        results.append(ReviewResult(image=image, rotation=rotation, discarded=discarded))

    if key_iter is None:
        cv2.destroyAllWindows()

    return results


# ---------------------------------------------------------------------------
# Helpers — also used by saver.py
# ---------------------------------------------------------------------------

def rotate_pil(image: Image.Image, degrees_clockwise: int) -> Image.Image:
    """Rotate a PIL image by a multiple of 90° clockwise using lossless transpose."""
    ops = {
        90:  Image.Transpose.ROTATE_270,  # PIL ROTATE_270 = 90° CW
        180: Image.Transpose.ROTATE_180,
        270: Image.Transpose.ROTATE_90,   # PIL ROTATE_90  = 90° CCW = 270° CW
    }
    op = ops.get(degrees_clockwise % 360)
    return image.transpose(op) if op else image.copy()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _handle_key(key: int) -> str:
    lo = key & 0xFF
    if lo == KEY_ESC:
        return "abort"
    if lo in KEY_ENTER:
        return "confirm"
    if lo in KEY_DISCARD:
        return "discard"
    if key in KEY_LEFT:
        return "rotate_ccw"
    if key in KEY_RIGHT:
        return "rotate_cw"
    return "unknown"


def _make_preview(image: Image.Image, rotation: int, index: int, total: int) -> np.ndarray:
    rotated = rotate_pil(image, rotation)
    preview = _scale_to_fit(rotated, _MAX_PREVIEW)
    bgr = cv2.cvtColor(np.array(preview.convert("RGB")), cv2.COLOR_RGB2BGR)
    _draw_overlay(bgr, index, total, rotation)
    return bgr


def _scale_to_fit(image: Image.Image, max_side: int) -> Image.Image:
    w, h = image.size
    scale = min(max_side / w, max_side / h, 1.0)
    if scale < 1.0:
        return image.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    return image


def _draw_overlay(bgr: np.ndarray, index: int, total: int, rotation: int) -> None:
    """Burn a semi-transparent instruction bar into the bottom of bgr (in-place)."""
    h, w = bgr.shape[:2]
    bar_h = 50

    # Semi-transparent dark bar
    overlay = bgr.copy()
    cv2.rectangle(overlay, (0, h - bar_h), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, bgr, 0.25, 0, bgr)

    font = cv2.FONT_HERSHEY_SIMPLEX
    top_y = h - bar_h + 18
    bot_y = h - bar_h + 38

    cv2.putText(bgr,
                f"Image {index} of {total}   Rotation: {rotation} deg",
                (10, top_y), font, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(bgr,
                "<- -> Rotate   D Discard   Enter Confirm   Esc Abort all",
                (10, bot_y), font, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
