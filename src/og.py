"""Open Graph cards, drawn with Pillow when the site is built: a sheet of the site's paper with the
title, the signature and the ink work in its corner."""

from dataclasses import dataclass
from functools import cache
from io import BytesIO

from PIL import Image, ImageChops, ImageDraw, ImageFont

from content import ASSETS_DIR, STATIC_DIR

WIDTH, HEIGHT = 1200, 630
MARGIN = 72

# The site's light palette: --paper, --ink-1 and --ink-4 in main.css, and the seal's red
PAPER = "#e9e4d8"
INK = "#100e0b"
INK_QUIET = "#5e5950"
SEAL = "#b11e1b"

# Latin and Cyrillic in one file: a title can hold both. In assets/, which the site never serves.
FONT = ASSETS_DIR / "spectral-300.ttf"

AUTHOR = "vladkens"

# A title starts at TITLE_MAX and steps down until it fits. What doesn't fit at TITLE_MIN stops the
# build, as an image without a size does. Everything stays left of the work: ART_BOX is its limit.
TITLE_BOX = (850, 330)
TITLE_TOP = 150
TITLE_MAX = 96
TITLE_MIN = 40
NOTE_BOX = (760, 80)
NOTE_MAX = 28
NOTE_MIN = 20
LEADING = 1.2
ART_BOX = (270, 300)


@dataclass(frozen=True)
class Card:
    title: str
    note: str  # the line at the foot: a post's date, an app's tagline


@cache
def font(size: int) -> ImageFont.FreeTypeFont:
    """Basic layout on purpose: Raqm comes and goes with the machine's FriBiDi, and so would the
    line breaks."""
    return ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.BASIC)


@cache
def glyph(c: str) -> bytes:
    x = Image.new("L", (TITLE_MAX * 2, TITLE_MAX * 2))
    ImageDraw.Draw(x).text((0, 0), c, font=font(TITLE_MAX), fill=255)
    return x.tobytes()


def missing_glyphs(text: str) -> str:
    """A letter the font hasn't got draws as the box a private-use one does."""
    return "".join(c for c in set(text) if glyph(c) == glyph("\U000f0000"))


def wrap(text: str, x: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines = []
    for word in text.split():
        line = f"{lines[-1]} {word}" if lines else word
        if lines and x.getlength(line) <= width:
            lines[-1] = line
        else:
            lines.append(word)

    return lines


def balanced(text: str, x: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """The narrowest box that takes no more lines, as `text-wrap: balance` does on the site."""
    lines = wrap(text, x, width)
    while width > 0 and len(wrap(text, x, width - 8)) == len(lines):
        width -= 8
        lines = wrap(text, x, width)

    return lines


def fit(
    text: str, box: tuple[int, int], top: int, low: int
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """The largest size at which `text` stays inside `box`. No word gets cut to get there."""
    width, height = box
    for size in range(top, low - 1, -2):
        x = font(size)
        lines = balanced(text, x, width)
        if len(lines) * size * LEADING <= height and all(x.getlength(y) <= width for y in lines):
            return x, lines

    raise ValueError(f"og: {text!r} doesn't fit a card, even at {low}px")


@cache
def paper() -> Image.Image:
    """The tile overlaid on the paper's tone: a card has a sheet's grain, the site's flat colour."""
    tile = Image.open(ASSETS_DIR / "paper.webp").convert("RGB")
    sheet = Image.new("RGB", (WIDTH, HEIGHT))
    for y in range(0, HEIGHT, tile.height):
        for x in range(0, WIDTH, tile.width):
            sheet.paste(tile, (x, y))

    return ImageChops.overlay(Image.new("RGB", (WIDTH, HEIGHT), PAPER), sheet)


@cache
def seal(size: int) -> Image.Image:
    """assets/seal.png is static/seal.svg at 256px: Pillow can't read an SVG.
    Only its alpha is used, and the colour comes from here."""
    mask = Image.open(ASSETS_DIR / "seal.png").getchannel("A")
    return mask.resize((size, size), Image.Resampling.LANCZOS)


@cache
def work() -> Image.Image:
    """The site's work in the left field, static/ink-roadworks.webp: the owner's avatar in ink."""
    x = Image.open(STATIC_DIR / "ink-roadworks.webp").convert("RGBA")

    # the avatar's empty margin cut away, so the ink itself reaches the corner
    x = x.crop(x.getchannel("A").getbbox())
    x.thumbnail(ART_BOX, Image.Resampling.LANCZOS)

    # the ink is in the file's alpha, over no paper
    return Image.alpha_composite(Image.new("RGBA", x.size, "white"), x).convert("RGB")


def draw_work(sheet: Image.Image) -> None:
    """Ink soaks into the paper: multiply. It stands in the corner."""
    x = work()
    left, top = WIDTH - x.width, HEIGHT - x.height
    sheet.paste(ImageChops.multiply(sheet.crop((left, top, WIDTH, HEIGHT)), x), (left, top))


def draw_lines(
    pen: ImageDraw.ImageDraw, x: ImageFont.FreeTypeFont, lines: list[str], top: float, fill: str
) -> None:
    step = x.size * LEADING
    for i, line in enumerate(lines):
        pen.text((MARGIN, top + (i + 0.5) * step), line, font=x, fill=fill, anchor="lm")


def draw_card(card: Card) -> bytes:
    gone = missing_glyphs(card.title + card.note)
    if gone:
        raise ValueError(f"og: {FONT.name} has no {gone!r}, used in {card.title!r}")

    sheet = paper().copy()
    pen = ImageDraw.Draw(sheet)
    draw_work(sheet)

    # the signature, as in the page's header
    small = font(30)
    pen.text((MARGIN, MARGIN), AUTHOR, font=small, fill=INK, anchor="lm")
    sheet.paste(SEAL, (MARGIN + round(small.getlength(AUTHOR)) + 20, MARGIN - 24), seal(48))

    x, lines = fit(card.title, TITLE_BOX, TITLE_MAX, TITLE_MIN)
    draw_lines(pen, x, lines, TITLE_TOP, INK)

    if card.note:
        x, lines = fit(card.note, NOTE_BOX, NOTE_MAX, NOTE_MIN)
        draw_lines(pen, x, lines, HEIGHT - MARGIN - len(lines) * x.size * LEADING, INK_QUIET)

    out = BytesIO()
    sheet.save(out, "PNG")
    return out.getvalue()
