import cv2
import numpy as np
from PIL import Image
from typing import List

from .detector import DetectedRegion


def deskew_regions(
    image: Image.Image,
    regions: List[DetectedRegion],
) -> List[Image.Image]:
    """
    Crop and deskew each detected region from the scan.

    Returns PIL Images in the same order as regions. Each image is rotated to
    axis-parallel alignment. Portrait vs landscape orientation is deliberately
    left to the interactive review step — the user rotates 90° there.
    """
    return [_extract_region(image, r) for r in regions]


def _extract_region(image: Image.Image, region: DetectedRegion) -> Image.Image:
    arr = _to_array(image)
    h_img, w_img = arr.shape[:2]

    # Padded bounding-box crop — gives the angle sweep a local view of the
    # document without dragging in the rest of the scan.
    x, y, rw, rh = region.bounding_box
    pad = max(rw, rh) // 8
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(w_img, x + rw + pad)
    y2 = min(h_img, y + rh + pad)
    crop = arr[y1:y2, x1:x2]

    ch, cw = crop.shape[:2]
    crop_center = (cw / 2.0, ch / 2.0)

    # Find the rotation angle that makes edges axis-parallel.
    deskew_angle = _find_skew_angle(crop)

    # Rotate the crop in-place (same output size, border filled with edge pixels).
    M = cv2.getRotationMatrix2D(crop_center, deskew_angle, 1.0)
    rotated_crop = cv2.warpAffine(
        crop, M, (cw, ch),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )

    # Map the quad corners (original image space) into the rotated crop space.
    quad_in_crop = region.quad - np.array([[x1, y1]], dtype=np.float32)
    ones = np.ones((4, 1), dtype=np.float32)
    rotated_corners = (M @ np.hstack([quad_in_crop, ones]).T).T  # (4, 2)

    rx1 = int(max(0, np.floor(rotated_corners[:, 0].min())))
    ry1 = int(max(0, np.floor(rotated_corners[:, 1].min())))
    rx2 = int(min(cw, np.ceil(rotated_corners[:, 0].max())))
    ry2 = int(min(ch, np.ceil(rotated_corners[:, 1].max())))

    return _to_pil(rotated_crop[ry1:ry2, rx1:rx2], image.mode)


def _find_skew_angle(region_arr: np.ndarray) -> float:
    """
    Return the rotation angle (degrees, OpenCV convention: positive = CCW) that
    makes the dominant edges in region_arr axis-parallel.

    Sweeps -45° to +45° in two passes (1° coarse, 0.1° fine) and picks the
    angle that maximises the combined variance of the horizontal and vertical
    projection profiles on the Canny edge image.
    """
    if region_arr.ndim == 3:
        gray = cv2.cvtColor(region_arr[:, :, :3], cv2.COLOR_RGB2GRAY)
    else:
        gray = region_arr

    # Downsample for speed — the optimal angle is scale-invariant.
    h, w = gray.shape
    max_dim = 600
    scale = min(1.0, max_dim / max(h, w, 1))
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1.0 else gray

    edges = cv2.Canny(small, 50, 150, apertureSize=3)
    sh, sw = edges.shape
    center = (sw / 2.0, sh / 2.0)

    def score(angle: float) -> float:
        Mc = cv2.getRotationMatrix2D(center, angle, 1.0)
        rot = cv2.warpAffine(edges, Mc, (sw, sh), flags=cv2.INTER_NEAREST)
        return float(np.var(rot.sum(axis=1))) + float(np.var(rot.sum(axis=0)))

    # Coarse pass: -45° to +45° in 1° steps.
    coarse = np.arange(-45.0, 46.0, 1.0)
    best_coarse = coarse[int(np.argmax([score(a) for a in coarse]))]

    # Fine pass: ±2° around the coarse best in 0.1° steps.
    fine = np.arange(best_coarse - 2.0, best_coarse + 2.05, 0.1)
    best_fine = fine[int(np.argmax([score(a) for a in fine]))]

    return float(best_fine)


# ---------------------------------------------------------------------------
# Array ↔ PIL helpers
# ---------------------------------------------------------------------------

def _to_array(image: Image.Image) -> np.ndarray:
    # warpAffine is purely geometric — channel order and colour mode don't
    # matter. Convert palette and CMYK modes to RGB so numpy gives a clean
    # 3-channel uint8 array; the save step restores the original format.
    if image.mode in ("P", "PA"):
        image = image.convert("RGBA" if "A" in image.mode else "RGB")
    elif image.mode == "CMYK":
        image = image.convert("RGB")
    return np.array(image)


def _to_pil(arr: np.ndarray, original_mode: str) -> Image.Image:
    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L")
    if arr.shape[2] == 4:
        return Image.fromarray(arr, mode="RGBA")
    return Image.fromarray(arr, mode="RGB")
