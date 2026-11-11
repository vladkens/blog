"""Fast rhythm check: reads static/ and the built public/. No browser, standard library only.

Catches what is wrong on paper: a stylesheet past its budget, what the owner's rules ban from it, a
var() nothing defines, a selector written twice, image steps that differ from the build's, a script
touching an image's size, a post image without the size the build gives it, a block Tab can land
on.

Can't catch what only exists once laid out: that takes a look in a browser.
"""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
STATIC = ROOT / "static"
CSS = STATIC / "main.css"
CODE_CSS = STATIC / "code.css"
SCRIPTS = [STATIC / "main.js", STATIC / "debug-menu.js"]
CONTENT = SRC / "content.py"
PUBLIC = ROOT / "public"

BUDGET = 785

BANNED = {
    "round()": r"\bround\(",
    ":has": r":has\(",
    "mask": r"\bmask",
    "!important": r"!important",
    "transform": r"\btransform\b",
    "filter": r"\bfilter\b",
    "a blend mode": r"-blend-mode",
    "a gradient": r"-gradient\(",
    "@font-face": r"@font-face",
    "a negative margin": r"margin[\w-]*:[^;]*(?<![\w-])-(?:\d|\.|1\)|var)|margin[\w-]*:[^;]*\*\s*-",
}

# The one place nothing else can do it: header holds the top of the window, the TOC a row under the
# signature, and the work the bottom
POSITIONS = ["sticky"]

# The exceptions, on these rules alone: the band's wash has to stand behind a link and take no room,
# and the toast, the zoomed picture and the debug menu hold their place in the window whatever
# scrolls, over the page
RULE_POSITIONS = {
    ("absolute", "nav a::before, .list a::before, .meta a::before, .cloud a::before, footer a::before"),
    ("relative", "nav a, .list a, .meta a, .cloud a, footer a"),
    ("fixed", ".toast"),
    ("fixed", ".zoom"),
    ("fixed", ".debug"),
}

# The one round(), on this rule alone: a short page fills the window in whole rows, and only the
# browser knows the window
ROUND_RULE = ("@supports (height: round(down, 100svh, 1px))", "body")

# The one thing tilted, by a value the build gives each page: a seal is stamped by hand
ROTATE_RULE = ".seal"

FONTS = {"ui-serif", "Georgia", "serif", "ui-monospace", "Menlo", "Consolas", "monospace"}

# What main.js can't do: an image's size is the build's and CSS's
JS_SIZING = re.compile(r"getBoundingClientRect|naturalWidth|naturalHeight|style\.(?:width|height)")

# Set by the build or by main.js, not in the CSS
BUILD_VARS = {"--lines", "--rows", "--ar", "--tilt", "--n"}

COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
VAR = re.compile(r"var\(\s*(--[\w-]+)")
DEFINED = re.compile(r"(--[\w-]+)\s*:")
STEP_RULE = re.compile(r"@media \(min-width: (\d+)px\) \{ img, svg \{ --rows: var\(--r(\d+)\); \} \}")
BASE_STEP = re.compile(r"--rows: var\(--r(\d+)\);\n  display: block;")
IMAGE_STEPS = re.compile(r"^IMAGE_STEPS = \((.*?)^\)", re.DOTALL | re.MULTILINE)

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}


def blank(m: re.Match) -> str:
    return re.sub(r"[^\n]", " ", m[0])


def line_of(text: str, at: int) -> int:
    return text.count("\n", 0, at) + 1


def rule_heads(text: str) -> list[tuple[str, str, int]]:
    """(the @media around it, selector, line) of each rule. Fails on what doesn't balance."""
    rs, stack, start = [], [], 0
    for i, ch in enumerate(text):
        if ch == ";":
            start = i + 1

        if ch == "{":
            head = " ".join(text[start:i].split())
            stack.append(head)
            start = i + 1

            if not head.startswith("@"):
                media = " ".join(x for x in stack[:-1] if x.startswith("@"))
                rs.append((media, head, line_of(text, i)))

        if ch == "}":
            if not stack:
                raise ValueError(f"line {line_of(text, i)}: a closing brace with nothing open")

            stack.pop()
            start = i + 1

    if stack:
        raise ValueError(f"`{stack[-1]}` is never closed")

    return rs


def check_css(path: Path, defined: set[str]) -> tuple[list[str], int]:
    raw = path.read_text(encoding="utf-8")
    text = COMMENT.sub(blank, raw)
    name = path.relative_to(ROOT)
    errs = []

    try:
        heads = rule_heads(text)
    except ValueError as e:
        return [*errs, f"{name}: {e}"], 0

    def rule_at(line: int) -> str:
        return next((x for _, x, at in reversed(heads) if at <= line), "")

    def allowed(why: str, line: int) -> bool:
        """ROUND_RULE's round(): in its rule, or in the @supports that holds it."""
        at = next(((m, x) for m, x, start in reversed(heads) if start <= line), None)
        head = text.splitlines()[line - 1].strip() == ROUND_RULE[0] + " {"
        return why == "round()" and (at == ROUND_RULE or head)

    for why, pattern in BANNED.items():
        errs += [
            f"{name}:{line_of(text, m.start())}: {why} is banned"
            for m in re.finditer(pattern, text)
            if not allowed(why, line_of(text, m.start()))
        ]

    for m in re.finditer(r"font(?:-family)?:([^;]+);", text):
        names = {x.split("/")[-1].split()[-1] for x in m[1].split(",")}
        if names - FONTS:
            errs.append(f"{name}:{line_of(text, m.start())}: fonts {names - FONTS} aren't system")

    for m in VAR.finditer(text):
        if m[1] not in defined and not re.fullmatch(r"--r\d+", m[1]):
            errs.append(f"{name}:{line_of(text, m.start())}: nothing defines {m[1]}")

    for m in re.finditer(r"\bposition:\s*([\w-]+)", text):
        line = line_of(text, m.start())

        if m[1] not in POSITIONS and (m[1], rule_at(line)) not in RULE_POSITIONS:
            errs.append(f"{name}:{line}: `position: {m[1]}`, no room for it")

    for m in re.finditer(r"\brotate:", text):
        line = line_of(text, m.start())

        if rule_at(line) != ROTATE_RULE:
            errs.append(f"{name}:{line}: `rotate` is only for {ROTATE_RULE}")

    seen = set()
    for media, selector, line in heads:
        if (media, selector) in seen:
            errs.append(f"{name}:{line}: `{selector}` is written twice")

        seen.add((media, selector))

    return errs, len(heads)


def image_steps() -> list[int]:
    m = IMAGE_STEPS.search(CONTENT.read_text(encoding="utf-8"))
    return [int(x) for x in re.findall(r"\d+", m[1])] if m else []


def check_steps(text: str) -> list[str]:
    """The build sizes an image at each step and CSS picks it: they have to name the same widths."""
    steps = image_steps()
    base = BASE_STEP.search(text)
    rules = [(int(a), int(b)) for a, b in STEP_RULE.findall(text)]
    errs = [f"{CSS.name}: min-width {a}px picks --r{b}" for a, b in rules if a != b]

    picked = [int(base[1])] if base else []
    picked += [a for a, _ in rules]
    if picked != steps:
        errs.append(f"{CSS.name} picks {picked}, {CONTENT.name} has {steps}")

    return errs


def check_scripts() -> list[str]:
    errs = []
    for path in SCRIPTS:
        text = path.read_text(encoding="utf-8")
        errs += [
            f"{path.relative_to(ROOT)}:{line_of(text, m.start())}: `{m[0]}`: no measuring in JS"
            for m in JS_SIZING.finditer(text)
        ]

    return errs


def inline(attrs: dict[str, str | None]) -> dict[str, str]:
    pairs = [x.split(":", 1) for x in (attrs.get("style") or "").split(";") if ":" in x]
    return {k.strip().lower(): v.strip() for k, v in pairs}


class Page(HTMLParser):
    def __init__(self, path: Path, steps: set[str]):
        super().__init__()
        self.path = path.relative_to(ROOT)
        self.steps = steps
        self.errs = []
        self.stack: list[tuple[str, list[str]]] = []
        self.counts = {"img": 0, "work": 0}

    def fail(self, why: str) -> None:
        self.errs.append(f"{self.path}:{self.getpos()[0]}: {why}")

    def inside(self, name: str) -> bool:
        return any(tag == name or name in classes for tag, classes in self.stack)

    def check_media(self, tag: str, attrs: dict[str, str | None]) -> None:
        """What CSS picks from: the wrapper, the real size and the rows at each step."""
        self.counts["img"] += 1

        name = attrs.get("src") or tag
        if not self.inside("media"):
            self.fail(f"{name}: not in a .media wrapper")

        if not (attrs.get("width") and attrs.get("height")):
            self.fail(f"{name}: no width and height attributes")

        style = inline(attrs)
        if not self.steps <= style.keys():
            self.fail(f"{name}: style must hold each step of {CSS.name}")
        elif not all(style[x].isdecimal() and int(style[x]) for x in self.steps):
            self.fail(f"{name}: a step isn't a whole number of rows")

    def check_work(self, attrs: dict[str, str | None]) -> None:
        self.counts["work"] += 1

        if not inline(attrs).get("--rows", "").isdecimal():
            self.fail(f"{attrs.get('src')}: a work needs --rows, its height on the page")

        if not (attrs.get("width") and attrs.get("height")):
            self.fail(f"{attrs.get('src')}: no width and height attributes")

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "img" and self.inside("art"):
            self.check_work(attrs)
        elif tag in ("img", "svg") and self.inside("article") and not self.inside("svg"):
            self.check_media(tag, attrs)

        if tag in ("pre", "table") and attrs.get("tabindex") != "-1":
            self.fail(f'a <{tag}> without tabindex="-1": Chromium tabs to whatever scrolls')

        if tag not in VOID:
            self.stack.append((tag, (attrs.get("class") or "").split()))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def check_public() -> tuple[list[str], dict[str, int]]:
    errs = []
    counts = {"page": 0, "img": 0, "work": 0}
    steps = {f"--r{x}" for x in image_steps()}

    for path in sorted(PUBLIC.rglob("*.html")):
        page = Page(path, steps)
        page.feed(path.read_text(encoding="utf-8"))
        page.close()
        errs += page.errs
        counts["page"] += 1

        for k, v in page.counts.items():
            counts[k] += v

    for name in ("img", "work"):
        if not counts[name]:
            errs.append(f"{PUBLIC.name}/: no {name} anywhere, so nothing was checked")

    return errs, counts


def main() -> None:
    started = perf_counter()

    if not (PUBLIC / "index.html").is_file():
        sys.exit(f"{PUBLIC.name}/ is missing or empty: run `make build` first")

    text = CSS.read_text(encoding="utf-8")
    lines = text.count("\n")
    defined = BUILD_VARS | set(DEFINED.findall(COMMENT.sub(blank, text)))

    errs = [f"{CSS.name}: {lines} lines, the budget is {BUDGET}"] if lines > BUDGET else []

    main_errs, rules = check_css(CSS, defined)
    code_errs, code_rules = check_css(CODE_CSS, defined)
    pages, counts = check_public()
    errs += main_errs + code_errs + check_steps(text) + check_scripts() + pages

    for x in errs:
        print(x, file=sys.stderr)

    if errs:
        sys.exit(f"rhythm: failed, {len(errs)} found")

    took = (perf_counter() - started) * 1000
    print(
        f"rhythm ok: {lines} lines, {rules + code_rules} rules, {counts['page']} pages, "
        f"{counts['img']} images, {counts['work']} works in {took:.0f}ms"
    )


if __name__ == "__main__":
    main()
