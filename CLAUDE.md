# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mitosis is a Python CLI tool that takes a single flatbed scan containing multiple documents, photos, or receipts and splits it into individual, deskewed, correctly oriented image files — preserving the original DPI, colour space, ICC profile, bit depth, and file format.

Full requirements are in [PRD.md](PRD.md).

## Setup

```bash
pip install opencv-python Pillow numpy click
```

## Running

```bash
python -m mitosis scan.png
# or once installed as a package:
mitosis scan.png
```

## Tests

```bash
python -m pytest tests/
python -m pytest tests/test_detector.py -v   # single module
```

Tests are synthetic — they generate scan images programmatically via Pillow, so no real scan files are needed.

## Architecture

The pipeline is linear and stateless between stages:

1. **Load** (Pillow) — read image and capture all metadata (DPI, ICC profile, mode, format)
2. **Detect** (OpenCV) — Canny edge detection → contour analysis → filter to rectangular regions
3. **Overlap check** — if any bounding boxes intersect, abort with no output written
4. **Deskew** (OpenCV) — `minAreaRect` per contour → rotate to axis-parallel alignment
5. **Review** (OpenCV `imshow`) — interactive per-image window; arrow keys rotate 90°, D discards, ESC aborts all
6. **Save** (Pillow) — write each confirmed image with original metadata restored

OpenCV uses BGR arrays; Pillow uses RGB. Channel swap is required on every Pillow→OpenCV and OpenCV→Pillow conversion.

## Key Constraints

- Output filenames always append `_a`, `_b`, `_c`... — even for single-document scans — to prevent overwriting the input file
- Discarded items keep their letter; the sequence is not renumbered
- JPEG output uses `quality=95, subsampling=0`; a warning is shown at startup if the input is JPEG
- No perspective correction — lid-closed flatbed scans are treated as optically flat
