import string
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

from .review import ReviewResult, rotate_pil


def save_results(
    results: List[ReviewResult],
    source_path: str,
    source_image: Image.Image,
) -> List[Path]:
    """
    Save each non-discarded ReviewResult next to the source file.

    Naming: {stem}_{letter}{ext} with letters a, b, c ... in detection order.
    Discarded items consume their letter so the sequence has gaps, not renumbers.
    Metadata (DPI, ICC profile, EXIF) is taken from source_image.info and
    written to every output file.

    Returns the list of Paths that were actually written.
    """
    source = Path(source_path)
    fmt = source_image.format or _ext_to_format(source.suffix)
    saved: List[Path] = []

    for i, result in enumerate(results):
        if result.discarded:
            continue

        letter = string.ascii_lowercase[i]
        out_path = source.parent / f"{source.stem}_{letter}{source.suffix}"

        final = rotate_pil(result.image, result.rotation)
        final = _ensure_compatible_mode(final, fmt)
        _write(final, out_path, fmt, source_image.info)
        saved.append(out_path)

    return saved


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _write(image: Image.Image, path: Path, fmt: str, info: Dict) -> None:
    kwargs: Dict = {}

    if "dpi" in info:
        kwargs["dpi"] = info["dpi"]
    if "icc_profile" in info:
        kwargs["icc_profile"] = info["icc_profile"]
    if "exif" in info:
        kwargs["exif"] = info["exif"]

    if fmt == "JPEG":
        kwargs["quality"] = 95
        kwargs["subsampling"] = 0
    elif fmt == "TIFF":
        # Preserve original compression; fall back to LZW (lossless, widely supported)
        compression = info.get("compression", "tiff_lzw")
        kwargs["compression"] = compression

    image.save(path, format=fmt, **kwargs)


def _ensure_compatible_mode(image: Image.Image, fmt: str) -> Image.Image:
    """Strip alpha before saving to formats that don't support it."""
    if fmt == "JPEG" and image.mode in ("RGBA", "LA", "P", "PA"):
        return image.convert("RGB")
    if fmt == "BMP" and image.mode not in ("RGB", "RGBA", "L"):
        return image.convert("RGB")
    return image


def _ext_to_format(ext: str) -> str:
    return {
        ".jpg": "JPEG", ".jpeg": "JPEG",
        ".png": "PNG",
        ".tif": "TIFF", ".tiff": "TIFF",
        ".bmp": "BMP",
    }.get(ext.lower(), "PNG")
