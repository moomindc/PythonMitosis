import sys
from pathlib import Path
import click
from PIL import Image, ImageOps

from .detector import detect_documents
from .deskew import deskew_regions
from .review import review_interactive
from .saver import save_results


@click.command()
@click.argument("image_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--min-area",
    default=0.05,
    show_default=True,
    metavar="FLOAT",
    help="Minimum document area as fraction of scan area.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Save debug images (debug_mask.png, debug_contours.png) showing detection results.",
)
def main(image_file: str, min_area: float, debug: bool) -> None:
    """Split a scanned image into individual documents."""
    _DEBUG_FILES = ("debug_mask.png", "debug_contours.png")
    if not debug:
        for name in _DEBUG_FILES:
            Path(name).unlink(missing_ok=True)

    image = Image.open(image_file)
    is_jpeg = image.format == "JPEG"

    # Bake any EXIF orientation into the pixels and reset the tag to 1 (normal),
    # so downstream steps and saved files are unambiguously pixel-correct.
    image = ImageOps.exif_transpose(image)

    if is_jpeg:
        click.echo(
            "Warning: input is JPEG — output files will be re-encoded at maximum "
            "quality (95). Some generation loss is unavoidable.",
            err=True,
        )

    # --- Detect ---
    click.echo(f"Detecting documents in {image_file} ...")
    try:
        regions = detect_documents(image, min_area_fraction=min_area, debug=debug)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    count = len(regions)
    click.echo(f"Found {count} document{'s' if count != 1 else ''}.")

    # --- Deskew ---
    click.echo("Deskewing ...")
    deskewed = deskew_regions(image, regions)

    # --- Review ---
    click.echo("Opening review window — use arrow keys to rotate, D to discard, Enter to confirm.")
    results = review_interactive(deskewed)

    confirmed = sum(1 for r in results if not r.discarded)
    discarded = len(results) - confirmed
    if discarded:
        click.echo(f"{discarded} image{'s' if discarded != 1 else ''} discarded.")
    if confirmed == 0:
        click.echo("No images to save.")
        sys.exit(0)

    # --- Save ---
    saved = save_results(results, image_file, image)
    click.echo(f"\nSaved {len(saved)} file{'s' if len(saved) != 1 else ''}:")
    for path in saved:
        click.echo(f"  {path}")


if __name__ == "__main__":
    main()
