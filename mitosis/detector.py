import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from PIL import Image


@dataclass
class DetectedRegion:
    """A single detected document region within a scan."""
    quad: np.ndarray  # (4, 2) float32 — four corner points in original image space
    angle: float      # rotation angle in degrees from minAreaRect, range [-90, 0)

    @property
    def bounding_box(self) -> Tuple[int, int, int, int]:
        """Axis-aligned bounding box as (x, y, w, h)."""
        x, y, w, h = cv2.boundingRect(self.quad.astype(np.int32))
        return x, y, w, h


def detect_documents(
    image: Image.Image,
    min_area_fraction: float = 0.05,
    debug: bool = False,
) -> List[DetectedRegion]:
    """
    Detect rectangular documents in a scanned image.

    Scans are assumed to have been taken with the lid closed on a flatbed scanner,
    producing a roughly uniform background behind the documents.

    Parameters
    ----------
    image:
        The full scan. Any PIL mode is accepted.
    min_area_fraction:
        Documents smaller than this fraction of the total image area are ignored.

    Returns
    -------
        Detected regions sorted top-to-bottom then left-to-right.

    Raises
    ------
    ValueError
        If no documents are found, or if any two detected regions overlap.
    """
    bgr = _pil_to_bgr(image)
    h, w = bgr.shape[:2]
    total_area = h * w
    min_area = total_area * min_area_fraction
    # Reject contours that fill almost the entire scan — these are the scanner
    # border or a hull that wraps all documents together.
    max_area = total_area * 0.90

    mask = _find_document_mask(bgr)

    if debug:
        _save_debug_image(bgr, mask, "debug_mask.png")

    # RETR_EXTERNAL on the filled-blob mask gives one outer contour per
    # document; internal photo content is invisible inside the filled blobs.
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = _build_regions(contours, min_area, max_area)

    # Canny + dilation produces both an inner and outer contour for each
    # document edge. Deduplicate them before checking for real overlaps.
    regions = _deduplicate(regions)

    if debug:
        _save_debug_contours(bgr, regions, "debug_contours.png")

    if not regions:
        raise ValueError(
            "No documents detected. Ensure documents have clearly defined edges "
            "against the scanner background, or lower --min-area."
        )

    _check_overlaps(regions)

    regions.sort(key=lambda r: (r.bounding_box[1], r.bounding_box[0]))
    return regions


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _pil_to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _find_document_mask(bgr: np.ndarray) -> np.ndarray:
    """
    Return a binary mask (white=document, black=background) suitable for
    contour finding. Uses background subtraction rather than edge detection so
    that photo content (faces, foliage, text) does not produce false contours.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    if np.median(gray) > 127:
        # Closed-lid flatbed: background is near-white. Estimate it from the
        # image corners, where no document can physically reach.
        margin = max(h, w) // 20
        corners = np.concatenate([
            gray[:margin, :margin].ravel(),
            gray[:margin, w - margin:].ravel(),
            gray[h - margin:, :margin].ravel(),
            gray[h - margin:, w - margin:].ravel(),
        ])
        # 90th-percentile of corner pixels ≈ pure scanner background.
        bg_level = int(np.percentile(corners, 90))
        # Pixels darker than bg_level - 20 are document content.
        threshold = max(bg_level - 20, 200)
        _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    else:
        # Dark background (lid open / dark platen): content is brighter.
        _, mask = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)

    # Large close fills any bright (near-white) areas inside photos so each
    # document becomes a solid filled blob.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=4)
    # Small open removes isolated noise specks outside document areas.
    kernel_sm = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_sm, iterations=2)
    return mask


def _build_regions(contours: list, min_area: float, max_area: float = float("inf")) -> List[DetectedRegion]:
    regions = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        # Require a roughly rectangular shape. Internal photo/document content
        # produces complex contours with many corners; documents produce 4–8.
        hull = cv2.convexHull(cnt)
        epsilon = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)
        if len(approx) > 8:
            continue

        rect = cv2.minAreaRect(cnt)
        quad = cv2.boxPoints(rect).astype(np.float32)  # (4, 2)
        angle = rect[2]
        regions.append(DetectedRegion(quad=quad, angle=angle))
    return regions


def _deduplicate(regions: List[DetectedRegion], iou_threshold: float = 0.85) -> List[DetectedRegion]:
    """
    Remove near-duplicate regions that arise because dilation produces both an
    inner and outer contour for each document boundary edge.

    Regions with IoU above iou_threshold are considered duplicates; the larger
    one (outer edge) is kept.
    """
    if len(regions) <= 1:
        return list(regions)

    # Process largest-first so we always keep the outer contour when merging.
    by_area = sorted(regions, key=lambda r: r.bounding_box[2] * r.bounding_box[3], reverse=True)
    kept: List[DetectedRegion] = []
    for candidate in by_area:
        if not any(_iou(candidate.bounding_box, k.bounding_box) > iou_threshold for k in kept):
            kept.append(candidate)
    return kept


def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    intersection = ix * iy
    if intersection == 0:
        return 0.0
    return intersection / (aw * ah + bw * bh - intersection)


def _check_overlaps(regions: List[DetectedRegion]) -> None:
    boxes = [r.bounding_box for r in regions]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if _rects_overlap(boxes[i], boxes[j]):
                raise ValueError(
                    f"Detected regions {i + 1} and {j + 1} overlap. "
                    "Ensure documents are not touching or overlapping on the scanner."
                )


def _rects_overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def _save_debug_image(bgr: np.ndarray, mask: np.ndarray, path: str) -> None:
    cv2.imwrite(path, mask)
    print(f"Debug: mask saved to {path}")


def _save_debug_contours(bgr: np.ndarray, regions: List[DetectedRegion], path: str) -> None:
    vis = bgr.copy()
    colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (0, 255, 255), (255, 0, 255)]
    for i, r in enumerate(regions):
        pts = r.quad.astype(np.int32).reshape(-1, 1, 2)
        color = colors[i % len(colors)]
        cv2.polylines(vis, [pts], True, color, 3)
        x, y, rw, rh = r.bounding_box
        label = f"#{i+1} {rw}x{rh}"
        cv2.putText(vis, label, (x, max(y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    cv2.imwrite(path, vis)
    print(f"Debug: {len(regions)} contour(s) drawn to {path}")
