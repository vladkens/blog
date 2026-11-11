"""Writes static/ink-roadworks.webp and -dark.webp: the owner's GitHub avatar, assets/roadworks.jpg,
a road sign with a man digging, painted over in ink. A demo of a work in the left field, until the
artist's page.

Nothing of the photo is kept but where things are. The sign is three strokes of a loaded brush, its
bristles running dry towards the lift; the man is the pictogram's shape as one mass of ink, its edge
soaked into the paper's fibres; the mound a grey wash with the pigment pooled at its rim. Painted on
wet paper, it runs soft and bleeds, and each file is one pale flat ink with the painting as alpha: a
wash behind the text, not a picture beside it.

Run: uv run --no-project --with pillow scripts/make-ink.py"""

import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "roadworks.jpg"
OUT = ROOT / "static"

# The photo's px, and how many times finer it's painted
SIZE = 460
K = 3
N = SIZE * K

# 7 rows of 32px, at 2x
WIDTH = 448

# The sign's corners on the middle of its red band, and the yellow inside it
APEX, LEFT, RIGHT = (236, 40), (22, 402), (440, 418)
FACE = [(238, 62), (40, 388), (421, 402)]

# Under the shovel's blade: the mound
HEAP = [(240, 340), (262, 322), (285, 312), (300, 305), (380, 305), (380, 365), (234, 365)]

# name -> ink, and how much of the painting's alpha it keeps: a pale wash, the wash of the links'
# band in each theme, so the work stays behind the text
INKS = {"": ((0x8A, 0x83, 0x74), 0.5), "-dark": ((0x8F, 0x89, 0x7D), 0.42)}

WEBP = {"format": "WEBP", "quality": 90, "alpha_quality": 100, "method": 6}


def lut(f) -> list[int]:
    return [max(0, min(255, round(f(v / 255) * 255))) for v in range(256)]


def tone(x: Image.Image, k: float) -> Image.Image:
    return x.point(lut(lambda v: v * k))


def ramp(x: Image.Image, at: float, width: float) -> Image.Image:
    return x.point(lut(lambda v: (v - at + width / 2) / width))


def smooth(a: float, b: float, t: float) -> float:
    t = min(1, max(0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def blur(x: Image.Image, r: float) -> Image.Image:
    return x.filter(ImageFilter.GaussianBlur(r * K))


def screen(*xs: Image.Image) -> Image.Image:
    out = xs[0]
    for x in xs[1:]:
        out = ImageChops.screen(out, x)

    return out


def noise(rng: random.Random, size: tuple[int, int], cells: tuple[int, int]) -> Image.Image:
    """Smooth noise, 0 to 255: `cells` random values across `size`. Drawn out along x, it's the grain a
    brush leaves in its stroke."""
    small = Image.frombytes("L", cells, rng.randbytes(cells[0] * cells[1]))
    return ImageOps.autocontrast(small.resize(size, Image.Resampling.BICUBIC), cutoff=1)


def fibres(rng: random.Random, cell: int) -> Image.Image:
    return noise(rng, (N, N), (N // (cell * K), N // (cell * K)))


def uneven(x: Image.Image, rng: random.Random, cell: int, k: float) -> Image.Image:
    return ImageChops.multiply(x, fibres(rng, cell).point(lut(lambda v: 1 - k + k * v)))


def ragged(mask: Image.Image, rng: random.Random, r=1.0, cell=3, amount=0.5) -> Image.Image:
    """Ink soaks into the paper's fibres: the edge wanders by their noise."""
    wander = fibres(rng, cell).point(lut(lambda v: (v - 0.5) * amount + 0.5))
    return ramp(ImageChops.add(blur(mask, r), wander, offset=-128), 0.5, 0.1)


def rims(x: Image.Image, r: float, k: float) -> Image.Image:
    """The pigment drifts to the edge of a wash as it dries: darker where the wash ends."""
    return screen(x, tone(ImageChops.subtract(x, blur(x, r)), k))


def inside(points: list[tuple[int, int]], shrink=0) -> Image.Image:
    x = Image.new("L", (N, N))
    ImageDraw.Draw(x).polygon([(a * K, b * K) for a, b in points], fill=255)
    return x.filter(ImageFilter.MinFilter(shrink * K * 2 + 1)) if shrink else x


def brush(rng: random.Random, a: tuple, b: tuple, width: float, ink: float, fly: float) -> Image.Image:
    """A stroke of a loaded brush from a to b, painted along x and turned into place: bristles side by
    side, landing in a round, a little wider where it presses. Towards the lift they run dry one by
    one, the edge ones first, and the paper shows through in streaks, the flying white: the lower
    `fly`, the sooner."""
    bristles = 56
    length = math.dist(a, b) * K
    w0 = width * K
    pad = int(w0)
    tile = Image.new("L", (int(length + 2 * pad), int(w0 * 1.6 + 2 * pad)))
    pen = ImageDraw.Draw(tile)
    mid = tile.height / 2

    def w(t: float) -> float:
        land = 0.8 + 0.2 * smooth(0, 0.06, t) + 0.15 * math.exp(-(((t - 0.05) / 0.05) ** 2))
        return w0 * land * (1 - 0.3 * smooth(0.65, 1, t))

    step = 1.5
    thick = max(2, round(w0 / bristles * 2.4))
    for i in range(bristles):
        off = (i + 0.5) / bristles * 2 - 1 + rng.uniform(-0.7, 0.7) / bristles
        dry = min(1 - rng.uniform(0, 0.05), rng.uniform(fly, 1.6) - 0.5 * abs(off) ** 1.5)
        x = pad + w(0) / 2 * (1 - math.sqrt(1 - off * off)) * rng.uniform(0.8, 1.1)

        while x < pad + length * dry:
            t = (x - pad) / length
            fade = smooth(dry - 0.35, dry, t)
            if rng.random() < 0.004 + fade * 0.06:
                x += rng.uniform(4, 30 + 120 * fade)
                continue

            y0, y1 = mid + off * w(t) / 2, mid + off * w(t + step / length) / 2
            pen.line([(x, y0), (x + step + 1, y1)], fill=255, width=thick)
            x += step

    grain = noise(rng, tile.size, (6, 70)).point(lut(lambda v: 0.88 + 0.12 * v))
    stroke = ImageChops.multiply(tone(tile.filter(ImageFilter.GaussianBlur(0.6)), ink), grain)

    # the page's px to the tile's: a lands on (pad, mid), b along x from it
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    c, s = math.cos(angle), math.sin(angle)
    ax, ay = a[0] * K, a[1] * K
    data = (c, s, pad - ax * c - ay * s, -s, c, mid + ax * s - ay * c)
    return stroke.transform((N, N), Image.Transform.AFFINE, data, Image.Resampling.BICUBIC)


def paint() -> Image.Image:
    rng = random.Random(7)
    photo = Image.open(SOURCE).convert("RGB").resize((N, N), Image.Resampling.LANCZOS).convert("HSV")
    dark = ramp(blur(photo.getchannel("V"), 0.6), 0.32, 0.1).point(lut(lambda v: 1 - v))
    shape = ImageChops.multiply(dark, inside(FACE, shrink=2))
    heap = ImageChops.multiply(shape, inside(HEAP))
    man = ImageChops.subtract(shape, heap)

    # the sign: three strokes, lifted at the apex where it hangs
    sides = screen(
        brush(rng, (APEX[0] - 8, APEX[1] + 6), (LEFT[0] + 4, LEFT[1] - 4), 24, 0.96, fly=0.75),
        brush(rng, (LEFT[0] - 2, LEFT[1] + 2), (RIGHT[0] + 2, RIGHT[1] + 2), 22, 0.94, fly=0.6),
        brush(rng, (RIGHT[0] - 2, RIGHT[1] - 12), (APEX[0] + 10, APEX[1] + 8), 23, 0.92, fly=0.5),
    )
    sides = screen(sides, tone(blur(sides, 1.2), 0.12))

    # the man: one mass of ink, its grain along his lean
    lean = noise(rng, (N * 2, N * 2), (16, 110)).rotate(-55, Image.Resampling.BICUBIC)
    lean = lean.crop((N // 2, N // 2, N // 2 + N, N // 2 + N)).point(lut(lambda v: 0.9 + 0.1 * v))
    man = ImageChops.multiply(tone(ragged(man, rng), 0.97), lean)

    # the mound: a grey wash, pooled at its rim and settled into the paper's grain
    heap = rims(tone(ragged(heap, rng, r=1.2, cell=4, amount=0.8), 0.5), 3, 1.6)
    heap = uneven(ImageChops.multiply(heap, fibres(rng, 1).point(lut(lambda v: 0.72 + 0.28 * v))), rng, 12, 0.3)

    # painted on wet paper: every stroke runs soft, and the ink bleeds out past its edge in a feathered halo
    painting = screen(sides, heap, man)
    painting = ImageChops.blend(painting, blur(painting, 1.6), 0.6)
    painting = screen(painting, uneven(tone(blur(painting, 5), 0.35), rng, 8, 0.6))
    painting = ImageChops.multiply(painting, fibres(rng, 1).point(lut(lambda v: 0.9 + 0.1 * v)))
    return painting.resize((WIDTH, WIDTH), Image.Resampling.LANCZOS)


def main() -> None:
    alpha = paint()
    for suffix, (ink, keep) in INKS.items():
        x = Image.new("RGBA", alpha.size, (*ink, 0))
        x.putalpha(tone(alpha, keep))
        x.save(OUT / f"ink-roadworks{suffix}.webp", **WEBP)


if __name__ == "__main__":
    main()
