"""Build the served images from the full-size originals in design/originals/.

Usage (from the project folder):  python tools/images/optimize_images.py

Originals are never changed or deployed. To change art, replace the original, run this,
and give a replaced WebP a new name if visitors should see it right away, since unversioned
images are cached for a day.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ORIGINALS = ROOT / "design" / "originals"
STATIC = ROOT / "static"

PROFILE_EDGE = 256  # shown at up to 80 CSS px, so this is sharp on 3x screens
PROFILES = [f"profile{n}button{face}.png" for n in ("", "2", "3", "4") for face in ("", "smile")]
BACKGROUNDS = {
    "homebackground.png": "homebackground.webp",
    "weighinsbackground.png": "weighinsbackground.webp",
    "workoutbackground9.png": "workoutbackground9.webp",
}
BACKGROUND_QUALITY = 90
PLATE_QUALITY = 92


def build():
    for name in PROFILES:
        im = Image.open(ORIGINALS / name).convert("RGBA")
        im.resize((PROFILE_EDGE, PROFILE_EDGE), Image.LANCZOS).save(STATIC / name, optimize=True)

    # The plate is displayed with `cover` in a square, so only the middle square ever shows.
    plate = Image.open(ORIGINALS / "weightplate.png").convert("RGBA")
    width, height = plate.size
    square = plate.crop(((width - height) // 2, 0, (width + height) // 2, height))
    square.save(STATIC / "weightplate.webp", quality=PLATE_QUALITY, method=6)

    for source, target in BACKGROUNDS.items():
        im = Image.open(ORIGINALS / source).convert("RGB")
        im.save(STATIC / target, quality=BACKGROUND_QUALITY, method=6)


if __name__ == "__main__":
    build()
    print("Images built in static/")
