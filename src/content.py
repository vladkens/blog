import glob
import json
import re
from base64 import b64decode
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from html import unescape
from io import BytesIO
from itertools import pairwise
from math import ceil, floor
from pathlib import Path
from urllib.parse import unquote, unquote_to_bytes, urljoin, urlsplit, urlunsplit

import pygments
import yaml
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml, unescapeAll
from markdown_it.renderer import RendererProtocol
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from markupsafe import Markup
from mdit_py_plugins.anchors import anchors_plugin
from PIL import Image
from pygments.filter import Filter
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexers.c_cpp import CFamilyLexer
from pygments.lexers.shell import BashLexer, ShellSessionBaseLexer
from pygments.token import Comment, Error, Keyword, Text
from pygments.util import ClassNotFound

SRC = Path(__file__).parent
ROOT = SRC.parent
PAGES_DIR = ROOT / "pages"
POSTS_DIR = ROOT / "posts"
DRAFTS_DIR = POSTS_DIR / "drafts"
APPS_DIR = PAGES_DIR / "apps"
STATIC_DIR = ROOT / "static"
ASSETS_DIR = ROOT / "assets"
PROJECTS = PAGES_DIR / "projects.json"

# fence language -> Pygments lexer
LEXERS = {"jsonc": "json5"}

# the fences that can hold a shell session, and what starts a command in one
SESSIONS = {"", "sh", "shell", "bash", "zsh", "console", "text", "txt", "plaintext"}
PROMPT = re.compile(r"^[❯$] ", re.MULTILINE)

# the word of a C directive, with its `#` when Pygments leaves that on
DIRECTIVE = re.compile(r"\s*#?\s*\w+")

# The pieces of a tag, by the tokenizer in the HTML standard. Space there is these five, not \s.
TAG_START = re.compile(r"<(/?)([a-z][^ \t\n\f\r/>]*)", re.IGNORECASE)
TAG_GAP = re.compile(r"[ \t\n\f\r/]*")
ATTR_NAME = re.compile(r"[^ \t\n\f\r/>][^ \t\n\f\r/>=]*")
ATTR_EQ = re.compile(r"[ \t\n\f\r]*=[ \t\n\f\r]*")
ATTR_BARE = re.compile(r"[^ \t\n\f\r>]*")

# raw HTML that stays out of the page: notes left in the source
HTML_COMMENT = re.compile(r"<!--(?:-?>|.*?--!?>)\n?", re.DOTALL)

# Elements whose content is text to a browser, whatever it looks like. Their end tag alone ends them.
RAW_TEXT = {
    *("iframe", "noembed", "noframes", "plaintext", "script"),
    *("style", "textarea", "title", "xmp"),
}

# what a post can say about an image's size or box: the build's own values replace it
SIZE_ATTRS = {"width", "height", "style"}

# The window widths an image gets its own height at, in CSS px: static/main.css picks one per step.
# Each is where a shape near 16:9 gains a row (1.82 and 1.905, the posts' own), where the row changes
# (600) or the column is full.
IMAGE_STEPS = (
    *(320, 360, 375, 415, 432, 469, 490, 524, 547, 579),
    *(600, 615, 642, 673, 703, 732, 752),
)

# The layout an image is sized for, in CSS px: the widest text column, the gutters on both sides,
# the row, and the row on a window narrower than PHONE.
COLUMN = 720
GUTTERS = 32
ROW = 32
ROW_SM = 30
PHONE = 600

# What static/main.css takes off the column around an image: a list or a quote indents by this many
# rows, and a quote's rule adds its px.
INDENT = 1
QUOTE_RULE = 2

# The widest an image gets in a table, in CSS px: a column's width is the browser's to choose. On a
# narrow window it gets the text column less TABLE_REST rows: both cells' padding and a short column of
# words beside it.
TABLE_IMAGE = 240
TABLE_REST = 4

# An image under this share of the room it has is centred: .narrow in static/main.css.
NARROW = 0.8

# what holds one address, whatever the tag
URL_ATTRS = {"href", "src", "poster"}

# A srcset's URLs. One can hold a comma, as a data: URL does; only a comma after it ends a candidate.
SRCSET_URL = re.compile(r"(^\s*|,\s*)(\S*[^\s,])")

# Lengths in CSS px. Without a unit it's px; em and % hang on what's around, so they aren't here.
SVG_LENGTH = re.compile(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)([a-z]*)\s*", re.IGNORECASE)
SVG_UNITS = {
    "": 1,
    "px": 1,
    "pt": 4 / 3,
    "pc": 16,
    "in": 96,
    "cm": 96 / 2.54,
    "mm": 96 / 25.4,
    "q": 96 / 101.6,
}

# The build can't open what isn't in the repo, so these sizes are pinned by hand. Any other external
# image stops the build: copy it next to the post, or add it here. Only the draft rhythm-fixture
# uses this: a page that goes out loads nothing from another host.
EXTERNAL_IMAGES = {
    "https://raw.githubusercontent.com/vladkens/apigen-ts/HEAD/logo.svg": (320, 80),
}

# EXIF orientations that turn a photo on its side. Chromium honours them, except in WebP.
SIDEWAYS = {5, 6, 7, 8}

# words per minute, close to the rates Zola's reading time came out at
READ_SPEED = {"en": 238, "ru": 200}

# A post gets a table of contents from this many h2 on. A week's heading is shortened there to its
# number and title.
TOC_MIN = 3
WEEK = re.compile(r"(?:Неделя|Week) (\d+)\. (.+)")

# A page's description: a search engine shows about this much
DESCRIPTION_MAX = 155

# A paragraph's inline tokens that don't give their content to its text: a break is a space, and an
# image's alt and raw HTML are nothing. A link or emphasis has none of its own, and its words follow.
TEXT_PARTS = {"softbreak": " ", "hardbreak": " ", "image": "", "html_inline": ""}

# Gives the ids Zola did, so old #fragment links keep working. ь and ъ are left out: they become "-"
TRANSLIT = str.maketrans("абвгдезийклмнопрстуфыэ", "abvgdeziiklmnoprstufye") | str.maketrans(
    {
        "ё": "io",
        "ж": "zh",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ю": "iu",
        "я": "ia",
    }
)


def page_url(slug: str, lang: str) -> str:
    return f"/{slug}/" if lang == "en" else f"/{lang}/{slug}/"


def tag_url(tag: str, lang: str) -> str:
    return page_url(f"tags/{tag}", lang)


@dataclass
class Doc:
    """A Markdown file and the page it makes. `slug` is that page's address in English, no slashes
    around it: `macmon`, `apps/macmon`, `about`."""

    slug: str
    lang: str
    path: str
    body: str
    title: str
    description: str | None = field(default=None, kw_only=True)  # else the first paragraph's

    @property
    def url(self) -> str:
        return page_url(self.slug, self.lang)


@dataclass
class Post(Doc):
    date: date
    tags: list[str]
    updated: date | None = None  # a change worth telling readers and search engines of
    medium: str | None = None
    devto: str | None = None
    draft: bool = False
    unlisted: bool = False

    @property
    def folder(self) -> Path:
        return (ROOT / self.path).parent

    @property
    def modified(self) -> date:
        return self.updated or self.date

    @property
    def mirrors(self) -> list[tuple[str, str]]:
        return [(k, v) for k, v in (("devto", self.devto), ("medium", self.medium)) if v]

    @property
    def words(self) -> int:
        text = " ".join(self.body.split("```")[::2])  # code fences don't count
        return len(re.findall(r"\w+(?:['’.]\w+)*", text))

    @property
    def minutes(self) -> int:
        return ceil(self.words / READ_SPEED[self.lang])


@dataclass
class App(Doc):
    order: int
    tagline: str
    blurb: str
    language: str
    repos: dict[str, str]  # label -> GitHub URL, the main one first
    links: dict[str, str] = field(default_factory=dict)  # label -> URL
    posts: list[str] = field(default_factory=list)  # slugs of the posts about it
    stars: int = 0  # from projects.json, all its repos together


@dataclass
class Section:
    """An h2 of a post, for its table of contents."""

    id: str
    label: str
    title: str


type Docs[T: Doc] = dict[tuple[str, str], T]
type Posts = Docs[Post]
type Apps = Docs[App]


def read_docs[T: Doc](kind: type[T], paths: list[Path], prefix: str = "") -> Docs[T]:
    rs = {}
    for path in paths:
        _, meta, body = path.read_text(encoding="utf-8").split("---\n", 2)
        x = kind(
            slug=prefix + path.parent.name,
            lang=path.stem,
            path=path.relative_to(ROOT).as_posix(),
            body=body,
            **yaml.safe_load(meta),
        )
        rs[x.slug, x.lang] = x

    return rs


def post_files() -> list[Path]:
    """posts/<year>/<slug>/: any depth is read, so a post outside a year folder stops the build
    instead of vanishing. posts/drafts/ is the owner's desk, never built."""
    return sorted(x for x in POSTS_DIR.glob("**/*.md") if not x.is_relative_to(DRAFTS_DIR))


def check_slugs() -> None:
    """The URL is the slug alone, so one slug under two years would be one address for two posts."""
    folders = defaultdict(set)
    for path in post_files():
        folders[path.parent.name].add(path.parent.relative_to(ROOT).as_posix())

    for slug, xs in folders.items():
        if len(xs) > 1:
            raise ValueError(f"post {slug} is in more than one folder: {', '.join(sorted(xs))}")


def read_posts(drafts: bool) -> Posts:
    check_slugs()

    rs = read_docs(Post, post_files())
    for x in rs.values():
        year = x.folder.parent.name
        if year != str(x.date.year):
            raise ValueError(f"{x.path}: `date` is {x.date}, so its year folder isn't {year}")

    return {k: x for k, x in rs.items() if drafts or not x.draft}


def read_pages() -> Docs[Doc]:
    # by name: pages/apps/ has the same depth, and a reader of its own
    return read_docs(Doc, sorted(PAGES_DIR.glob("about/*.md")))


def read_apps() -> Apps:
    """Sorted by `order`. Stars that can't be known stop the build, as image sizes do."""

    def shared(x: App) -> tuple:
        return x.order, x.language, list(x.repos.values())

    apps = read_docs(App, sorted(APPS_DIR.glob("*/*.md")), "apps/")
    stars = {x["name"]: x["stars"] for x in json.loads(PROJECTS.read_text(encoding="utf-8"))}

    for x in apps.values():
        names = [url.removeprefix("https://github.com/") for url in x.repos.values()]
        missing = [name for name in names if name not in stars]
        if missing:
            raise ValueError(f"{x.path}: {missing} not in {PROJECTS.name}, run `make update`")

        x.stars = sum(stars[name] for name in names)

        # the languages share these, and the stars come from them
        en = apps[x.slug, "en"]
        if shared(x) != shared(en):
            raise ValueError(f"{x.path}: order, language or repos differ from {en.path}")

    return dict(sorted(apps.items(), key=lambda kv: kv[1].order))


def list_posts(posts: Posts, lang: str) -> list[Post]:
    rs = [x for x in posts.values() if x.lang == lang]
    rs += [x for x in posts.values() if x.lang == "en" and (x.slug, lang) not in posts]
    return sorted(rs, key=lambda x: x.date, reverse=True)


def list_tags(posts: Posts, lang: str) -> dict[str, list[Post]]:
    """Tag -> the posts on its page, by name. A language has a tag when a post written in it carries
    the tag, and that page then lists what the post list would: English posts with no translation
    too, marked `en`. A tag only English posts carry has no page in another language."""
    tags = sorted({tag for x in posts.values() if x.lang == lang for tag in x.tags})
    rs = list_posts(posts, lang)
    return {tag: [x for x in rs if tag in x.tags] for tag in tags}


def app_posts(app: App, posts: Posts) -> list[Post]:
    """In the app's language where the post has it. A wrong slug stops the build."""
    rs = [posts.get((x, app.lang)) or posts.get((x, "en")) for x in app.posts]
    if None in rs:
        raise ValueError(f"{app.path}: `posts` names a post that doesn't exist: {app.posts}")

    return rs


# MARK: Markdown


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().translate(TRANSLIT)).strip("-")


class Directives(Filter):
    """Pygments gives a C directive one token, so nothing in it gets a colour. This keeps the word
    as a keyword and lexes the rest as C. A piece of a line can end in what C alone calls an error,
    such as the `\\` of a macro going on."""

    def filter(self, lexer, stream):
        word = False
        for kind, value in stream:
            if kind is not Comment.Preproc:
                yield kind, value
                continue

            if value == "#":
                word = True
                yield Keyword, value
                continue

            m = DIRECTIVE.match(value) if word or value.startswith("#") else None
            word = False

            if m:
                yield Keyword, m[0]
                value = value[m.end() :]

            for _, t, v in lexer.get_tokens_unprocessed(value):
                yield Text if t is Error else t, v


class SessionLexer(ShellSessionBaseLexer):
    """A line with a prompt is a bash command, and the rest is its output. The stock lexer takes
    more for a prompt, and a line of output that opens with `(x)` for a virtualenv."""

    _innerLexerCls = BashLexer
    _ps1rgx = re.compile(r"^([❯$] )(.*\n?)")
    _ps2 = "> "
    _venv = re.compile(r"(?!)")


def highlight(code: str, lang: str) -> str:
    lang = lang.lower()
    if lang == "session":
        lexer = SessionLexer(stripnl=False)
    else:
        lexer = get_lexer_by_name(LEXERS.get(lang, lang), stripnl=False)

    if isinstance(lexer, CFamilyLexer):
        lexer.add_filter(Directives())

    return pygments.highlight(code, lexer, HtmlFormatter(nowrap=True)).rstrip("\n")


def code_block(code: str, lang: str = "") -> str:
    """Code never wraps, so its height is known here: three lines to two rows, one row of air, and
    up to whole rows, so the text below is back on a line."""
    code = code.strip("\n")
    lines = code.count("\n") + 1
    rows = ceil(lines * 2 / 3 + 1)
    if lang.lower() in SESSIONS and PROMPT.search(code):
        lang = "session"

    html = highlight(code, lang) if lang else escapeHtml(code)
    cls = f' class="language-{escapeHtml(lang)}"' if lang else ""

    # Chromium makes what scrolls a tab stop, and a table takes the same in rewrite_urls
    pre = f'<pre tabindex="-1"><code{cls}>{html}</code></pre>'

    # What stays put while the code scrolls can't stand in pre: main.js adds the copy button here
    return f'<div class="code" style="--lines: {lines}; --rows: {rows}">{pre}</div>\n'


def render_fence(self: RendererProtocol, tokens: list[Token], i: int, options, env) -> str:
    info = unescapeAll(tokens[i].info).split()
    return code_block(tokens[i].content, info[0] if info else "")


def render_code_block(self: RendererProtocol, tokens: list[Token], i: int, options, env) -> str:
    return code_block(tokens[i].content)


def demote_h1(state: StateCore) -> None:
    """The post title is the page's h1, so a `# Heading` in a body is one level down."""
    for x in state.tokens:
        if x.type in ("heading_open", "heading_close") and x.tag == "h1":
            x.tag = "h2"


def link_headings(state: StateCore) -> None:
    for i, x in enumerate(state.tokens):
        if x.type != "heading_open":
            continue

        link = Token("link_open", "a", 1)
        link.attrs = {"class": "zola-anchor", "href": f"#{x.attrGet('id')}"}

        inline = state.tokens[i + 1]
        inline.children = [link, *inline.children, Token("link_close", "a", -1)]


def collect_sections(state: StateCore) -> None:
    """Each h2, when render() asks for them."""
    rs = state.env.get("sections")
    if rs is None:
        return

    tokens = state.tokens
    for i, x in enumerate(tokens):
        # a heading without a slug has no anchor to go to
        if x.type == "heading_open" and x.tag == "h2" and x.attrGet("id"):
            kids = tokens[i + 1].children or []
            title = "".join(c.content for c in kids if c.type in ("text", "code_inline"))
            m = WEEK.fullmatch(title)
            rs.append(Section(x.attrGet("id"), f"{m[1]} {m[2]}" if m else title, title))


def describe(doc: Doc) -> str:
    """The page's summary for search and shared links: its own `description`, or the text of its
    first paragraph that has words, with no headings, code or images. A long one ends at a word, with
    an ellipsis."""
    text = doc.description or ""
    tokens = [] if text else plain_md.parse(doc.body)

    for x, inline in pairwise(tokens):
        if x.type != "paragraph_open":
            continue

        text = "".join(TEXT_PARTS.get(c.type, c.content) for c in inline.children)
        if text.strip():
            break

    text = " ".join(text.split())
    if len(text) <= DESCRIPTION_MAX:
        return text

    cut = text[: DESCRIPTION_MAX - 1]
    if text[len(cut)] != " ":
        cut = cut.rpartition(" ")[0]

    return cut.rstrip(" ,;:.-–—") + "…"


def toc(sections: list[Section]) -> list[Section]:
    """Too few sections to need one: none at all."""
    return sections if len(sections) >= TOC_MIN else []


def localize(href: str, lang: str, urls: set[str]) -> str:
    """`urls` is every page of the site. A page without this language keeps its English address."""
    url = urlsplit(href)
    slug = url.path.strip("/")
    path = page_url(slug, lang)
    if url.scheme or url.netloc or url.path != page_url(slug, "en") or path not in urls:
        return href

    return urlunsplit(url._replace(path=path))


def rewrite_link(x: Token, lang: str, urls: set[str]) -> None:
    href = str(x.attrGet("href"))
    url = urlsplit(href)
    if url.scheme in ("http", "https") or url.netloc:
        x.attrSet("target", "_blank")
        x.attrSet("rel", "noopener external")
        return

    x.attrSet("href", localize(href, lang, urls))


# MARK: Raw HTML


@dataclass
class Attr:
    name: str
    value: str  # entities decoded
    text: str  # as the post has it, with the space before it

    def set(self, value: str) -> None:
        if value != self.value:
            self.value = value
            self.text = f' {self.name}="{escapeHtml(value)}"'


@dataclass
class Tag:
    name: str
    head: str  # up to the attributes: `<img`
    closing: bool
    attrs: list[Attr] = field(default_factory=list)
    tail: str = ""  # after the attributes: ` />`

    @property
    def text(self) -> str:
        return self.head + "".join(x.text for x in self.attrs) + self.tail

    @property
    def void(self) -> bool:
        """`/>` means something only in an <svg>, which it really closes."""
        return self.tail.endswith("/>")

    def get(self, name: str) -> Attr | None:
        """The first one: a browser ignores the rest."""
        return next((x for x in self.attrs if x.name == name), None)


@dataclass
class Scan:
    """Where a post's raw HTML stands. An inline tag reaches us alone, so this lasts the whole post."""

    raw: str | None = None  # the RAW_TEXT element we are in
    svg: int = 0  # <svg> tags open
    picture: int = 0  # <picture> tags open
    lists: int = 0  # <ul> and <ol> open, raw or from Markdown
    quotes: int = 0  # <blockquote> open
    tables: int = 0  # <table> open
    images: int = 0  # <img> so far, raw or from Markdown


def read_tag(html: str, at: int) -> Tag | None:
    """The tag at `at`, or None if it never ends: a browser drops that one."""
    m = TAG_START.match(html, at)
    x = Tag(m[2].lower(), m[0], m[1] == "/")
    i = m.end()

    while True:
        gap = i
        i = TAG_GAP.match(html, i).end()
        if i == len(html):
            return None

        if html[i] == ">":
            x.tail = html[gap : i + 1]
            return x

        m = ATTR_NAME.match(html, i)
        name, i = m[0].lower(), m.end()

        m = ATTR_EQ.match(html, i)
        if m is None:
            x.attrs.append(Attr(name, "", html[gap:i]))
            continue

        i = m.end()
        quote = html[i : i + 1]
        if quote in ('"', "'"):
            end = html.find(quote, i + 1)
            if end < 0:
                return None

            value, i = html[i + 1 : end], end + 1
        else:
            m = ATTR_BARE.match(html, i)
            value, i = m[0], m.end()

        x.attrs.append(Attr(name, unescape(value), html[gap:i]))


def read_html(html: str, scan: Scan) -> Iterator[str | Tag]:
    """Cuts HTML as a browser does: its tags, and all the rest as it stands. Comments go."""
    i = 0
    while i < len(html):
        if scan.raw:
            m = re.compile(rf"</{scan.raw}(?=[ \t\n\f\r/>])", re.IGNORECASE).search(html, i)
            end = m.start() if m else len(html)
            yield html[i:end]

            i = end
            scan.raw = None if m else scan.raw
            continue

        at = html.find("<", i)
        if at < 0:
            yield html[i:]
            return

        yield html[i:at]
        i = at

        if html.startswith("<!--", i):
            m = HTML_COMMENT.match(html, i)
            if m is None:
                yield html[i:]
                return

            i = m.end()
            continue

        if TAG_START.match(html, i) is None:
            if html[i + 1 : i + 2] not in ("!", "?", "/"):
                yield "<"
                i += 1
                continue

            # a doctype and the like, up to the first > and not past it. CDATA is real in an <svg> alone.
            stop = "]]>" if scan.svg and html.startswith("<![CDATA[", i) else ">"
            end = html.find(stop, i)
            if end < 0:
                yield html[i:]
                return

            yield html[i : end + len(stop)]
            i = end + len(stop)
            continue

        x = read_tag(html, i)
        if x is None:
            yield html[i:]
            return

        i += len(x.text)
        yield x

        if x.name in RAW_TEXT and not x.closing and not (scan.svg and x.void):
            scan.raw = x.name


# MARK: Image sizes


def svg_length(value: str) -> float | None:
    m = SVG_LENGTH.fullmatch(value)
    if m is None or m[2].lower() not in SVG_UNITS:
        return None

    return float(m[1]) * SVG_UNITS[m[2].lower()]


def svg_size(tag: Tag) -> tuple[float, float] | None:
    """An <svg>'s shape, as a browser finds it: absolute width and height, or else the viewBox."""
    w, h = (svg_length(x.value) if x else None for x in (tag.get("width"), tag.get("height")))
    if w and h and w > 0 and h > 0:
        return w, h

    box = tag.get("viewbox")
    box = re.split(r"[\s,]+", box.value.strip()) if box else []
    try:
        w, h = float(box[2]), float(box[3])
    except IndexError, ValueError:
        return None

    return (w, h) if len(box) == 4 and w > 0 and h > 0 else None


def svg_text_size(text: str) -> tuple[float, float] | None:
    tags = (x for x in read_html(text, Scan()) if isinstance(x, Tag))
    tag = next((x for x in tags if x.name == "svg" and not x.closing), None)
    return svg_size(tag) if tag else None


def shown_size(x: Image.Image) -> tuple[float, float]:
    w, h = x.size
    return (h, w) if x.format != "WEBP" and x.getexif().get(0x0112) in SIDEWAYS else (w, h)


def file_size(path: Path) -> tuple[float, float] | None:
    if path.suffix.lower() == ".svg":
        return svg_text_size(path.read_text(encoding="utf-8"))

    with Image.open(path) as x:
        return shown_size(x)


def data_size(src: str) -> tuple[float, float] | None:
    """A data: URL carries its own file, so it's read like one."""
    head, _, body = src.partition(",")
    data = unquote_to_bytes(body.partition("#")[0])
    if head.lower().endswith(";base64"):
        data = b64decode(data)

    if "svg" in head.lower():
        return svg_text_size(data.decode())

    with Image.open(BytesIO(data)) as x:
        return shown_size(x)


def image_size(src: str, post: Doc) -> tuple[float, float]:
    """An image's real size. What can't be known stops the build: a guess would leave the grid."""
    url = urlsplit(src)
    if url.scheme == "data":
        try:
            size = data_size(src)
        except (OSError, ValueError) as e:
            raise ValueError(f"{post.path}: can't read data: image {src[:40]}...: {e}") from e

        if size is None:
            raise ValueError(f"{post.path}: data: image {src[:40]}... has no size of its own")

        return size

    if url.scheme or url.netloc:
        if src not in EXTERNAL_IMAGES:
            raise ValueError(
                f"{post.path}: external image {src}: its size can't be read at build time, "
                "copy it next to the post or add it to EXTERNAL_IMAGES in content.py"
            )

        return EXTERNAL_IMAGES[src]

    name = unquote(url.path).lstrip("/")
    paths = [*POSTS_DIR.glob(f"*/{glob.escape(name)}"), STATIC_DIR / name]
    if name.startswith("apps/"):
        paths = [PAGES_DIR / name]

    path = next((x for x in paths if x.is_file()), None)
    if path is None:
        raise ValueError(
            f"{post.path}: image {src} is not in posts/, pages/apps/ or static/"
        )

    size = file_size(path)
    if size is None:
        raise ValueError(f"{post.path}: {path.name} has no viewBox, and no width and height")

    return size


def enter(scan: Scan, tag: str, by: int) -> None:
    """Counts what narrows an image. A raw tag and a Markdown token both name theirs the same."""
    if tag in ("ul", "ol"):
        scan.lists = max(0, scan.lists + by)

    if tag == "blockquote":
        scan.quotes = max(0, scan.quotes + by)

    if tag == "table":
        scan.tables = max(0, scan.tables + by)


def room(step: int, row: int, scan: Scan) -> float:
    """The width an image has on a window this wide, where `scan` stands."""
    indent = (scan.lists + scan.quotes) * INDENT * row + scan.quotes * QUOTE_RULE
    width = min(step - GUTTERS, COLUMN) - indent
    return min(width - TABLE_REST * row, TABLE_IMAGE) if scan.tables else width


def rows(size: tuple[float, float], step: int, scan: Scan) -> int:
    """An image's height in whole rows on a window this wide. Its width follows from the height, so
    rounding down keeps the whole picture inside what `room` gives, or its own width if narrower."""
    w, h = size
    row = ROW_SM if step < PHONE else ROW
    return max(1, floor(min(w, room(step, row, scan)) * h / w / row))


def narrow(size: tuple[float, float], scan: Scan) -> bool:
    """An image clearly narrower than the text on the widest window. On a smaller one it only gets
    closer to the column, and in a table the column is the browser's."""
    w, h = size
    step = IMAGE_STEPS[-1]
    return not scan.tables and rows(size, step, scan) * ROW * w / h < NARROW * room(step, ROW, scan)


def size_style(size: tuple[float, float], scan: Scan) -> str:
    """What the page gets from the build: the ratio, and the height in rows at each step."""
    w, h = size
    steps = "; ".join(f"--r{x}: {rows(size, x, scan)}" for x in IMAGE_STEPS)
    return f"--ar: {w:g} / {h:g}; {steps}"


def sized(tag: Tag, size: tuple[float, float], scan: Scan) -> str:
    """Gives an opening tag the build's size."""
    w, h = size
    if narrow(size, scan):
        cls = tag.get("class")
        if cls:
            cls.set(f"{cls.value} narrow")
        else:
            tag.attrs.append(Attr("class", "narrow", ' class="narrow"'))

    attrs = "".join(x.text for x in tag.attrs if x.name not in SIZE_ATTRS)
    return f'{tag.head}{attrs} width="{w:g}" height="{h:g}" style="{size_style(size, scan)}">'


def post_src(src: str, slug: str) -> str:
    url = urlsplit(src)
    if url.scheme or url.netloc or src.startswith("/"):
        return src

    return f"/{slug}/{src.removeprefix('./')}"


def srcset_urls(srcset: str) -> list[str]:
    return [x[1] for x in SRCSET_URL.findall(srcset)]


# MARK: Rewriting


def loading(scan: Scan) -> dict[str, str]:
    """How the browser fetches the next picture. The first is most likely the cover, the largest
    thing in the first screen, and goes first; the rest wait until the reader gets near them."""
    scan.images += 1
    return {"fetchpriority": "high"} if scan.images == 1 else {"loading": "lazy", "decoding": "async"}


def rewrite_raw_img(x: Tag, scan: Scan, post: Doc) -> str:
    attr = x.get("src")
    if attr is None or not attr.value.strip():
        raise ValueError(f"{post.path}: {x.text} has no src")

    attr.set(post_src(attr.value.strip(), post.slug))
    for k, v in loading(scan).items():
        if not x.get(k):
            x.attrs.append(Attr(k, v, f' {k}="{v}"'))

    tag = sized(x, image_size(attr.value, post), scan)
    return tag if scan.picture else f'<span class="media">{tag}</span>'


def rewrite_raw_svg(x: Tag, scan: Scan, post: Doc) -> str:
    size = svg_size(x)
    if size is None:
        raise ValueError(f"{post.path}: {x.text} has no viewBox, and no width and height")

    scan.svg = 0 if x.void else 1
    end = "</svg></span>" if x.void else ""
    return f'<span class="media">{sized(x, size, scan)}{end}'


def rewrite_start(x: Tag, scan: Scan, post: Doc, urls: set[str]) -> str:
    href = x.get("href")
    if href:
        href.set(localize(href.value, post.lang, urls))

    if scan.svg:
        scan.svg += x.name == "svg" and not x.void
        return x.text

    enter(scan, x.name, 1)

    srcset = x.get("srcset")
    if srcset:
        srcset.set(SRCSET_URL.sub(lambda m: m[1] + post_src(m[2], post.slug), srcset.value))

    if x.name == "img":
        return rewrite_raw_img(x, scan, post)

    if x.name == "svg":
        return rewrite_raw_svg(x, scan, post)

    if x.name == "picture":
        scan.picture += 1
        return f'<span class="media">{x.text}' if scan.picture == 1 else x.text

    return x.text


def rewrite_end(x: Tag, scan: Scan) -> str:
    """Only the end of what we wrapped closes the wrapper."""
    if not scan.svg:
        enter(scan, x.name, -1)

    if x.name == "svg" and scan.svg:
        scan.svg -= 1
        return x.text if scan.svg else f"{x.text}</span>"

    if x.name == "picture" and scan.picture and not scan.svg:
        scan.picture -= 1
        return x.text if scan.picture else f"{x.text}</span>"

    return x.text


def rewrite_html(x: Token, scan: Scan, post: Doc, urls: set[str]) -> None:
    rs = []
    for tag in read_html(x.content, scan):
        if isinstance(tag, str):
            rs.append(tag)
        elif tag.closing:
            rs.append(rewrite_end(tag, scan))
        else:
            rs.append(rewrite_start(tag, scan, post, urls))

    x.content = "".join(rs)


def rewrite_image(x: Token, scan: Scan, post: Doc) -> None:
    src = post_src(str(x.attrGet("src")), post.slug)
    size = image_size(src, post)
    w, h = size

    x.attrSet("src", src)
    x.attrSet("width", f"{w:g}")
    x.attrSet("height", f"{h:g}")
    x.attrSet("style", size_style(size, scan))
    for k, v in loading(scan).items():
        x.attrSet(k, v)

    if narrow(size, scan):
        x.attrJoin("class", "narrow")


def render_image(self: RendererProtocol, tokens: list[Token], i: int, options, env) -> str:
    html = self.image(tokens, i, options, env)
    return html if tokens[i].meta.get("bare") else f'<span class="media">{html}</span>'


def rewrite_urls(state: StateCore) -> None:
    post, urls = state.env["post"], state.env["urls"]
    scan = Scan()

    for block in state.tokens:
        enter(scan, block.tag, block.nesting)

        if block.type == "table_open":
            block.attrSet("tabindex", "-1")

        if block.type == "html_block":
            rewrite_html(block, scan, post, urls)

        for x in block.children or []:
            if x.type == "link_open":
                rewrite_link(x, post.lang, urls)

            if x.type == "html_inline":
                rewrite_html(x, scan, post, urls)

            if x.type == "image":
                x.meta["bare"] = bool(scan.raw or scan.svg or scan.picture)
                if not (scan.raw or scan.svg):
                    rewrite_image(x, scan, post)

    # the wrapper closes with the tag: without it the rest of the post lands inside the image
    if scan.svg or scan.picture:
        raise ValueError(f"{post.path}: an <svg> or <picture> is never closed")


md = MarkdownIt("commonmark", {"html": True}).enable("table")
md.use(anchors_plugin, max_level=6, slug_func=slugify)
md.add_render_rule("fence", render_fence)
md.add_render_rule("code_block", render_code_block)
md.add_render_rule("image", render_image)
md.core.ruler.push("demote_h1", demote_h1)
md.core.ruler.push("link_headings", link_headings)
md.core.ruler.push("rewrite_urls", rewrite_urls)
md.core.ruler.push("collect_sections", collect_sections)

# the same Markdown with none of the rules above, for describe() to read a page's text
plain_md = MarkdownIt("commonmark", {"html": True}).enable("table")


def absolute_html(html: Markup, base: str) -> str:
    """Rendered HTML with every address in full, for reading away from the site, as in a feed. The
    scan runs on a plain str: a slice of Markup stays Markup, and escapes what is added to it."""
    rs = []
    for x in read_html(str(html), Scan()):
        if isinstance(x, str):
            rs.append(x)
            continue

        for attr in x.attrs:
            if attr.name in URL_ATTRS:
                attr.set(urljoin(base, attr.value.strip()))

            if attr.name == "srcset":
                attr.set(SRCSET_URL.sub(lambda m: m[1] + urljoin(base, m[2]), attr.value))

        rs.append(x.text)

    return "".join(rs)


def render(post: Doc, urls: set[str], sections: list[Section] | None = None) -> Markup:
    """`sections`, when given, is filled with the post's h2."""
    try:
        return Markup(md.render(post.body, {"post": post, "urls": urls, "sections": sections}))
    except ClassNotFound as e:
        raise ValueError(f"{post.path}: {e}") from e
