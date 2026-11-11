"""Writes static/paper.webp and paper-dark.webp: the grain of assets/paper.webp as a tile for each
theme, in its final colours, so the page needs no blend mode.

Writes static/wash*.webp too: assets/wash*.webp are dry-brush strokes kept as alpha, baked for each
theme as one flat ink and trimmed to the stroke, so the page needs no mask and a link's band runs as
far past its text as its box does.

Run: uv run --no-project --with pillow scripts/make-art.py"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static"
SCANS = ROOT / "assets"
GRAIN = SCANS / "paper.webp"

WEBP = {"format": "WEBP", "quality": 90, "alpha_quality": 100, "method": 6}

# file -> --paper in static/main.css, as RGB. Lossless: the grain is a few levels deep, so a lossy
# tile shows its blocks, and takes the dark paper a level off --paper.
PAPERS = {"paper": (0xE9, 0xE4, 0xD8), "paper-dark": (0x15, 0x14, 0x12)}

# file suffix -> ink and how much of the stroke's alpha it keeps. The text on it sets the ceiling:
# --ink-3, the faintest there, stays at 4.5:1 on the wettest pixel.
WASHES = {"": ((0x8A, 0x83, 0x74), 0.48), "-dark": ((0x6E, 0x69, 0x5E), 0.45)}


def save(path: Path, grey: Image.Image, ink: tuple[int, ...], lut: list[int]) -> None:
    x = Image.new("RGBA", grey.size, (*ink, 0))
    x.putalpha(grey.point(lut))
    x.save(path, **WEBP)


def overlay(paper: int, grain: int) -> int:
    """`overlay` of CSS compositing, by the channel: the paper is the backdrop, the grain on it."""
    b, s = paper / 255, grain / 255
    x = 2 * b * s if b <= 0.5 else 1 - 2 * (1 - b) * (1 - s)
    return round(x * 255)


def tint(grain: Image.Image, paper: tuple[int, ...]) -> Image.Image:
    bands = zip(grain.split(), paper)
    return Image.merge("RGB", [x.point([overlay(c, v) for v in range(256)]) for x, c in bands])


def wash(name: str) -> None:
    grey = Image.open(SCANS / f"{name}.webp").convert("RGBA").getchannel("A")
    grey = grey.crop(grey.point([255 * (v > 24) for v in range(256)]).getbbox())

    for suffix, (ink, keep) in WASHES.items():
        save(OUT / f"{name}{suffix}.webp", grey, ink, [round(v * keep) for v in range(256)])


def main() -> None:
    grain = Image.open(GRAIN).convert("RGB")
    for name, paper in PAPERS.items():
        tint(grain, paper).save(OUT / f"{name}.webp", format="WEBP", lossless=True, method=6)

    for name in ("wash", "wash-short"):
        wash(name)


if __name__ == "__main__":
    main()
