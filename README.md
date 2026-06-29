# Mitosis

**Turn one messy flatbed scan into a folder of clean, individual files — automatically.**

You scan a stack of old photos, a handful of receipts, or a mix of documents all at once. Now you're left with a single image containing everything, crookedly placed and awkwardly cropped. Mitosis detects each item, straightens it, lets you confirm the orientation, and saves each one as its own file — preserving the original DPI, colour profile, bit depth, and format exactly.

```
scan.png  (one scan, three items)
    → scan_a.png   ✓ a receipt
    → scan_b.png   ✓ a photo
    → scan_c.png   ✓ another photo
```

No cloud upload. No subscription. No GUI to install. Just a command.

---

![Demo](https://private-user-images.githubusercontent.com/65719344/613988915-7b2b1af8-3301-4d7f-aab9-a992f1c2a089.gif?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3ODI3MjM2NDEsIm5iZiI6MTc4MjcyMzM0MSwicGF0aCI6Ii82NTcxOTM0NC82MTM5ODg5MTUtN2IyYjFhZjgtMzMwMS00ZDdmLWFhYjktYTk5MmYxYzJhMDg5LmdpZj9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNjA2MjklMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjYwNjI5VDA4NTU0MVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTZmOTQ5NGE3MDRlYzQ2YTVkY2EwYzI0ODViMzk1OGUyMzg3OTdlNWNkNmY4NTE5ZTY0OWZjYTU1ODk4NDE5MzMmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JnJlc3BvbnNlLWNvbnRlbnQtdHlwZT1pbWFnZSUyRmdpZiJ9.PB6SDaSvgrhDga6yxeVI7lK3gLyw85XJl8HXDyaC4Ag)

## Features

- **Automatic detection** — finds rectangular documents, photos, and receipts on a flatbed scan using edge detection and contour analysis
- **Deskew** — corrects small rotations so each item comes out axis-aligned
- **Interactive orientation review** — preview each item and rotate in 90° steps before saving; discard false positives
- **Lossless metadata preservation** — DPI, ICC colour profile, bit depth, and colour mode are carried through unchanged
- **Safe by default** — the original file is never touched; output always uses a `_a`, `_b`, `_c`… suffix
- **Abort at any point** — press `Esc` during review and nothing is written to disk

---

## Requirements

- Python 3.10 or later
- Windows, macOS, or Linux

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Mitosis.git
cd Mitosis
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` at the start of your prompt when the environment is active.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

```
python -m mitosis [OPTIONS] IMAGE_FILE
```

### Arguments

| Argument | Description |
|---|---|
| `IMAGE_FILE` | Path to the scan to process |

### Options

| Option | Default | Description |
|---|---|---|
| `--min-area FLOAT` | `0.05` | Minimum document size as a fraction of the total scan area. Lower this if small items (receipts, stamps) are not being detected. |
| `--debug` | off | Save `debug_mask.png` and `debug_contours.png` to the current directory, showing the detection mask and detected contours. Without this flag, any debug files left over from a previous run are deleted automatically. |
| `--help` | | Show help and exit |

### Examples

```bash
# Split a scan containing two photos
python -m mitosis holiday_scan.png

# Lower the minimum size threshold to detect small receipts
python -m mitosis receipts.tiff --min-area 0.02

# Save detection debug images to diagnose what was found
python -m mitosis my_scan.png --debug
```

---

## Interactive review

After detection and deskewing, a preview window opens for each found item:

| Key | Action |
|---|---|
| `←` Left arrow | Rotate 90° counter-clockwise |
| `→` Right arrow | Rotate 90° clockwise |
| `Enter` or `Space` | Confirm and move to next item |
| `D` | Discard this item (it will not be saved) |
| `Esc` | Abort — no files are written |

---

## Supported formats

| Format | Read | Write | Notes |
|---|---|---|---|
| PNG | ✓ | ✓ | Lossless |
| TIFF | ✓ | ✓ | Lossless; preserves multi-channel colour |
| JPEG | ✓ | ✓ | Re-encoding is lossy; a warning is shown at startup |
| BMP | ✓ | ✓ | Lossless |

All output files preserve the original DPI, ICC colour profile, bit depth, and colour mode (RGB, CMYK, greyscale, etc.).

---

## Output file naming

Output files are written to the same folder as the input, with a letter suffix appended before the extension:

```
scan.png → scan_a.png, scan_b.png, scan_c.png …
```

The suffix is always added — even when only one item is found — so the original file is never overwritten. If you discard an item during review, its letter is skipped (gaps in the sequence are intentional).

---

## Scanner tips

- **Scan with the lid closed.** A uniform background makes edge detection reliable.
- **Leave a gap between items.** Overlapping documents cannot be separated and will produce an error. A few millimetres is enough.
- **Scan at the highest DPI your workflow needs.** The tool preserves whatever DPI the file carries.
- **JPEG scans lose quality on every save.** If you need to re-edit the output files, scan as PNG or TIFF instead.

---

## Running the tests

```bash
python -m pytest tests/
```

Tests generate synthetic scan images programmatically — no real scan files are needed.

---

## Troubleshooting

**"No documents detected"**
Lower `--min-area`. The default (0.05) requires each item to cover at least 5% of the scan. A small receipt on a large flatbed may fall below this.

**"Detected regions overlap"**
Two items are touching or overlapping on the scanner. Re-scan with a visible gap between them.

**Items are detected but the wrong number are found**
Shadows, scanner frame edges, or high-contrast content within a document can be mistaken for separate items. Try adjusting `--min-area` upward to filter out small false positives.

**Using `--debug` to diagnose detection**
Run with `--debug` to produce two images in the current directory:
- `debug_mask.png` — the binary mask used to find documents (white = document, black = background)
- `debug_contours.png` — the original scan with detected contours drawn on it

These files are deleted automatically on the next run without `--debug`.

---

## Backlog

- PDF input support
- Batch processing of a folder (`--batch`)
- Output directory option (`--output-dir`)
