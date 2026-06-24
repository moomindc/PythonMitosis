# PRD: Mitosis

## Overview

A Python command-line tool that takes a single scanned image containing one or more physical documents, photos, or receipts and outputs them as separate, deskewed, correctly oriented image files — preserving the original file's colour depth, colour space, DPI, and format exactly.

## Goals

- Detect and extract individual items from a flatbed scan automatically
- Deskew each extracted item (rotation only — no perspective correction required; scanner lid is closed)
- Present each extracted item to the user for 90° orientation correction
- Allow the user to discard false positives during review
- Save output files with full fidelity to the original scan's image properties
- Warn (but proceed) when input is JPEG, as re-encoding is lossy

## Non-Goals (Backlog)

- PDF input/output
- Batch/folder processing
- Perspective warp correction
- Sub-90° manual fine-tuning of rotation (the deskew step handles this)
- GUI or web interface

---

## User Flow

```
$ mitosis scan.png

Detecting documents... found 3.
⚠ Input is JPEG — output will be re-encoded at maximum quality (95). Original will not be modified.

[Interactive preview opens]
  Image 1 of 3  |  ← → rotate 90°  |  D discard  |  Enter confirm
  Image 2 of 3  ...
  Image 3 of 3  ...

Saving:
  scan_a.png  ✓
  scan_b.png  (discarded)
  scan_c.png  ✓

Done. 2 files saved.
```

---

## Functional Requirements

### FR1 — Input

- Accept a single image file as a positional argument
- Supported formats: PNG, TIFF, JPEG, BMP
- Read and retain: DPI, ICC colour profile, bit depth, colour mode (RGB, RGBA, L, CMYK, etc.), file format

### FR2 — Document Detection

- Use Canny edge detection followed by contour analysis to locate distinct rectangular items
- Filter contours by:
  - Minimum area: configurable, default to be tuned during implementation (starting point: 5% of scan area)
  - Approximated polygon must have 4 corners (roughly rectangular)
- If any two detected bounding boxes overlap: abort with a clear error, produce no output files
- If zero documents detected: abort with a clear error
- If exactly one document is detected: proceed normally through deskew and review; output receives `_a` suffix

### FR3 — Deskewing

- For each detected item, compute the minimum-area bounding rectangle
- Extract the rotation angle from that rectangle
- Crop and rotate the region to align it axis-parallel
- No perspective warp — assume flat documents on a closed flatbed scanner

### FR4 — Interactive Orientation Review

- Open a native window (via `cv2.imshow`) showing a scaled preview of each extracted item, one at a time
- Display: filename that will be saved, item index (e.g. "2 of 3"), current rotation state
- Controls:
  - `←` / `→` arrow keys: rotate preview 90° counter-clockwise / clockwise
  - `D`: discard this item (will not be saved)
  - `Enter` or `Space`: confirm and move to next item
  - `ESC`: abort entire operation — no files written
- Rotation state accumulates; preview updates immediately

### FR5 — Output

- Save each confirmed image using the original file's format, DPI, ICC profile, bit depth, and colour mode
- Naming: `{original_name}_{letter}{extension}` where letter is `a`, `b`, `c`... in detection order
- Discarded items consume their letter — output filenames are not renumbered (gaps in sequence are acceptable)
- The input file is never overwritten; the `_a` suffix is always applied even for single-document scans
- JPEG output: save at quality=95, `subsampling=0` (best chroma fidelity)
- Write files to the same directory as the input file

### FR6 — JPEG Warning

- If input format is JPEG, print a warning before the interactive step explaining that re-encoding is lossy and cannot be avoided

---

## Error Cases

| Condition | Behaviour |
|---|---|
| Overlapping detected regions | Print error with overlap description; exit code 1; no files written |
| Zero documents detected | Print error with suggestion to check image or adjust `--min-area`; exit 1 |
| Unsupported file format | Print error listing supported formats; exit 1 |
| File not found | Standard OS error; exit 1 |
| User presses ESC in review | Print "Aborted — no files written"; exit 0 |
| All items discarded | Print warning; exit 0 |

---

## CLI Interface

```
mitosis [OPTIONS] IMAGE_FILE

Options:
  --min-area FLOAT    Minimum document area as fraction of scan area [default: 0.05]
  --help              Show this message and exit.
```

---

## Technical Architecture

```
main()
 ├── parse_args()
 ├── load_image()            # Pillow — preserves all metadata
 ├── detect_documents()      # OpenCV — Canny + contour analysis
 ├── check_overlaps()        # Reject if any bounding boxes intersect
 ├── deskew_all()            # OpenCV — minAreaRect + rotation crop
 ├── review_interactive()    # OpenCV imshow loop, returns [(image, rotation, discard)]
 └── save_results()          # Pillow — restores DPI, ICC, mode, format
```

**Image handoff**: Load with Pillow → convert to NumPy array for OpenCV processing → convert back to Pillow Image for saving. OpenCV works in BGR; Pillow in RGB — swap channels on each conversion.

---

## Dependencies

| Package | Purpose |
|---|---|
| `opencv-python` | Detection, deskewing, interactive preview |
| `Pillow` | Image I/O, metadata preservation |
| `numpy` | Array interop between Pillow and OpenCV |
| `click` | CLI argument parsing |

---

## Decisions Log

| # | Decision | Rationale |
|---|---|---|
| 1 | `_a` suffix always applied, even for single-document scans | Prevents overwriting the original input file |
| 2 | Discarded items keep their letter; sequence gaps are acceptable | Preserves spatial order; avoids renumbering complexity |
| 3 | Rotation in review step is 90° increments only | Deskew (FR3) handles sub-degree correction |
| 4 | Overlapping documents: hard reject, no output | Ambiguous crop boundaries make a best-guess unsafe |
| 5 | No perspective correction | Lid-closed flatbed scans are optically flat |
| 6 | JPEG re-encode at quality=95, subsampling=0 | Maximum practical quality; warn user that generation loss is unavoidable |

---

## Backlog

- PDF input support
- Batch/folder mode (`--batch DIR`)
- Output directory flag (`--output-dir`)
- Fine-grained rotation (1° increments) in review step
- Configuration file for persistent defaults
