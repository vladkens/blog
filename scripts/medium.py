"""Pushes a post's English version to Medium as a draft: a new one, or the same draft again with the
text replaced, and sets its canonical link and tags. Medium takes the SEO title and description and
the story's card from the text itself. Medium's API takes no new integrations and can't edit a
post, so this speaks the web editor's own protocol: the paragraph deltas it sends, and its GraphQL
for settings.

The login is the owner's own, read from Helium by unjar (https://github.com/vladkens/unjar).
curl_cffi passes for Chrome, as the Cloudflare in front of Medium wants. Headless Helium draws SVGs,
which Medium doesn't take.

  uv run python scripts/medium.py <slug>              # create the draft, or update the one it made
  uv run python scripts/medium.py <slug> --id <url>   # update this post instead
  uv run python scripts/medium.py <slug> --new        # always a new draft
  uv run python scripts/medium.py <slug> --tags "Rust,Open Source"   # set Medium's tags
  uv run python scripts/medium.py --find rust dictation               # Medium's tags, by followers
  uv run python scripts/medium.py <slug> --dry        # print the paragraphs, touch nothing
"""

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
from base64 import b64decode, b64encode
from html import escape
from io import BytesIO
from math import ceil
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

from curl_cffi import CurlMime, requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from content import (
    POSTS_DIR,
    STATIC_DIR,
    Post,
    plain_md,
    read_posts,
    svg_text_size,
)

SITE = "https://vladkens.me"
MEDIUM = "https://medium.com"
# what goes under every story, in Markdown as a post; no file, no footer
FOOTER = ROOT / "assets" / "mirrors" / "medium.md"
# slug -> the id of the draft made for it
DRAFTS = Path.home() / ".config" / "medium" / "drafts.json"
HELIUM = os.environ.get("MEDIUM_BROWSER", "/Applications/Helium.app/Contents/MacOS/Helium")
# the owner's Medium cookies, from the default profile of the browser above
UNJAR = ["unjar", "-b", "helium", "-f", "json", "medium.com"]

# a story takes this many tags at most
TAGS_MAX = 5

# Medium's paragraph, markup and delta types, as its editor sends them
P, H3, IMG, BQ, PRE, ULI, OLI, H4 = 1, 3, 4, 6, 8, 9, 10, 13
STRONG, EM, LINK, CODE = 1, 2, 3, 10
INSERT, DELETE, UPDATE, SECTION, UNSECTION = 1, 2, 3, 8, 9
KINDS = {P: "P", H3: "H3", IMG: "IMG", BQ: "BQ", PRE: "PRE", ULI: "UL", OLI: "OL", H4: "H4"}

# every API answer starts with this, against JSON hijacking
GUARD = "])}while(1);</x>"

# deltas per request: the editor sends up to 30
CHUNK = 30

# fence language -> Medium's; any other is plain text
LANGS = {"sh": "bash", "bash": "bash", "zsh": "bash", "shell": "bash", "console": "bash"}
LANGS |= {"ts": "typescript", "tsx": "typescript", "js": "javascript", "jsx": "javascript"}
LANGS |= {"py": "python", "rs": "rust", "yml": "yaml", "jsonc": "json", "html": "xml"}
LANGS |= {x: x for x in ("c", "cpp", "css", "go", "java", "json", "kotlin", "lua", "python")}
LANGS |= {x: x for x in ("rust", "sql", "swift", "typescript", "javascript", "yaml", "makefile")}

# Medium's widest image, in pixels: an SVG is drawn this wide, at a whole scale up to the most
SVG_WIDTH, SVG_SCALE = 1400, 3

# an SVG's dark theme, made to never apply: Medium has none
DARK = re.compile(r"prefers-color-scheme:\s*dark")

IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
SVG = re.compile(r"<svg\b.*?</svg>", re.IGNORECASE | re.DOTALL)
ATTR = re.compile(r"""\b(src|alt|aria-label)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
POST_ID = re.compile(r"([0-9a-f]{10,12})(?:/edit)?/?(?:[?#].*)?$")


def warn(msg: str) -> None:
    print(f"medium: {msg}", file=sys.stderr)


# MARK: Markdown


def name() -> str:
    return secrets.token_hex(2)


def utf16(text: str) -> int:
    """Offsets of markups count as JavaScript does."""
    return len(text.encode("utf-16-le")) // 2


def para(kind: int, text: str, markups: list[dict] | None = None) -> dict:
    return {"name": name(), "type": kind, "text": text, "markups": markups or []}


def svg_image(svg: str) -> dict:
    """An inline <svg>, carried as a data: URL till it gets drawn."""
    attrs = {m[1].lower(): m[2] or m[3] for m in ATTR.finditer(svg[: svg.find(">")])}
    src = "data:image/svg+xml;base64," + b64encode(svg.encode()).decode()
    return {"type": IMG, "src": src, "alt": attrs.get("aria-label", "")}


def html_images(html: str) -> list[dict]:
    rs = [svg_image(x) for x in SVG.findall(html)]
    for tag in IMG_TAG.findall(html):
        attrs = {m[1].lower(): m[2] or m[3] for m in ATTR.finditer(tag)}
        if attrs.get("src"):
            rs.append({"type": IMG, "src": attrs["src"], "alt": attrs.get("alt", "")})

    return rs


def inline(tokens: list, base: str) -> tuple[str, list[dict], list[dict]]:
    """A paragraph's text and markups, and the images in it, which Medium only has as paragraphs."""
    text, markups, images, opened, svg = "", [], [], [], None
    for x in tokens:
        match x.type:
            # an <svg> comes in pieces: its tags, and the text inside them
            case "html_inline" if svg is not None or x.content.lower().startswith("<svg"):
                svg = (svg or "") + x.content
                if x.content.lower().startswith("</svg"):
                    images.append(svg_image(svg))
                    svg = None
            case "text" if svg is not None:
                svg += escape(x.content, quote=False)
            case "text":
                text += x.content
            case "softbreak":
                text += " "
            case "hardbreak":
                text += "\n"
            case "code_inline":
                at = utf16(text)
                text += x.content
                markups.append({"type": CODE, "start": at, "end": utf16(text)})
            case "strong_open" | "em_open" | "link_open":
                opened.append((x, utf16(text)))
            case "strong_close" | "em_close" | "link_close":
                tag, at = opened.pop()
                if at == utf16(text):
                    continue

                m = {"start": at, "end": utf16(text)}
                if tag.type == "link_open":
                    href = urljoin(base, str(tag.attrGet("href")))
                    m |= {"type": LINK, "href": href, "title": "", "rel": "", "anchorType": 0}
                else:
                    m["type"] = STRONG if tag.type == "strong_open" else EM
                markups.append(m)
            case "image":
                alt = "".join(c.content for c in x.children or [])
                images.append({"type": IMG, "src": str(x.attrGet("src")), "alt": alt})
            case "html_inline":
                if re.fullmatch(r"<br\s*/?>", x.content, re.IGNORECASE):
                    text += "\n"
                images += html_images(x.content)

    return text, markups, images


def cell_text(tokens: list) -> str:
    return "".join(" " if x.type == "softbreak" else x.content for x in tokens if x.type != "image")


def table(tokens: list) -> str:
    """Medium has no tables: one in monospace, with the columns lined up as in the source."""
    rows, right = [], []
    for x in tokens:
        if x.type == "tr_open":
            rows.append([])
        if x.type == "th_open":
            right.append("right" in str(x.attrGet("style") or ""))
        if x.type == "inline":
            rows[-1].append(cell_text(x.children or []))

    widths = [max(len(r[k]) for r in rows) for k in range(len(right))]
    lines = [
        "  ".join(c.rjust(w) if k else c.ljust(w) for c, w, k in zip(r, widths, right, strict=True))
        for r in rows
    ]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(x.rstrip() for x in lines)


def code(text: str, lang: str = "") -> dict:
    lang = LANGS.get(lang.lower(), "")
    x = para(PRE, text.rstrip("\n"))
    # mode 1 is the editor guessing the language, 2 one set by hand, 0 none
    x["codeBlockMetadata"] = {"mode": 2, "lang": lang} if lang else {"mode": 0, "lang": ""}
    return x


def convert(post: Post) -> tuple[list[dict], list[int]]:
    """The post as Medium's paragraphs, the title and subtitle first, and the paragraphs that start
    a section (after a `---`). An image paragraph has its `src` until it is uploaded."""
    base = SITE + post.url
    body = post.body.rstrip() + ("\n\n" + FOOTER.read_text() if FOOTER.exists() else "")
    tokens = plain_md.parse(body)

    rs = [para(H3, post.title)]
    if post.description:
        rs.append(para(H4, post.description))

    breaks, lists, quotes, i = [], [], 0, 0
    while i < len(tokens):
        x = tokens[i]
        i += 1
        match x.type:
            case "bullet_list_open" | "ordered_list_open":
                lists.append(ULI if x.type == "bullet_list_open" else OLI)
            case "bullet_list_close" | "ordered_list_close":
                lists.pop()
            case "blockquote_open":
                quotes += 1
            case "blockquote_close":
                quotes -= 1
            case "hr":
                breaks.append(len(rs))
            case "fence":
                info = x.info.split()
                rs.append(code(x.content, info[0] if info else ""))
            case "code_block":
                rs.append(code(x.content))
            case "table_open":
                end = next(k for k in range(i, len(tokens)) if tokens[k].type == "table_close")
                rs.append(code(table(tokens[i:end])))
                i = end + 1
            case "html_block":
                images = html_images(x.content)
                if not images and not x.content.lstrip().startswith("<!--"):
                    warn(f"left out raw HTML: {x.content.strip()[:60]}")
                rs += images
            case "inline":
                prev = tokens[i - 2]
                if prev.type == "heading_open":
                    kind = H3 if prev.tag in ("h1", "h2") else H4
                else:
                    kind = lists[-1] if lists else BQ if quotes else P

                text, markups, images = inline(x.children or [], base)
                if text.strip():
                    rs.append(para(kind, text.strip("\n"), markups))
                rs += images

    for x in rs:
        if x["type"] == IMG:
            x |= {"name": name(), "text": "", "markups": [], "layout": 1}

    # Medium takes no empty section: rules in a row or at the end are one or none
    return rs, sorted({x for x in breaks if x < len(rs)})


# MARK: Images


def image_file(src: str, post: Post) -> tuple[str, bytes]:
    """A data: URL holds an inline SVG, a relative src is beside the post, /<slug>/<file> beside
    that post, any other path is in static/, and a URL gets downloaded."""
    url = urlsplit(src)
    if url.scheme == "data":
        head, _, data = src.partition(",")
        return "inline.svg", b64decode(data) if head.endswith(";base64") else unquote(data).encode()

    if url.scheme in ("http", "https"):
        with urlopen(Request(src, headers={"User-Agent": "vladkens.me"}), timeout=30) as rep:
            return Path(url.path).name, rep.read()

    path = unquote(url.path)
    if not path.startswith("/"):
        return Path(path).name, (post.folder / path).read_bytes()

    slug, _, rest = path.lstrip("/").partition("/")
    found = sorted(POSTS_DIR.glob(f"*/{slug}/{rest}")) if rest else []
    file = found[0] if found else STATIC_DIR / path.lstrip("/")
    return file.name, file.read_bytes()


def draw_svg(svg: str, w: int, h: int, scale: int) -> bytes:
    """An SVG as PNG on white, in its light colors, by headless Helium on a throwaway profile."""
    with tempfile.TemporaryDirectory(prefix="medium-") as tmp:
        src, out = Path(tmp, "image.svg"), Path(tmp, "image.png")
        src.write_text(DARK.sub("max-width: 0px", svg), encoding="utf-8")
        args = [HELIUM, "--headless", f"--user-data-dir={tmp}/profile", "--no-first-run"]
        args += ["--hide-scrollbars", "--default-background-color=ffffffff"]
        args += [f"--window-size={w},{h}", f"--force-device-scale-factor={scale}"]
        args += [f"--screenshot={out}", src.as_uri()]
        subprocess.run(args, check=True, capture_output=True, timeout=60)
        return out.read_bytes()


def raster(filename: str, data: bytes) -> tuple[str, str, bytes, int, int]:
    """What Medium shows: PNG, JPEG and GIF as they are, an SVG drawn by the browser, the rest
    redone as PNG (Medium takes a WebP, then its CDN never serves it). Name, type, bytes, size."""
    stem = Path(filename).stem
    if Path(filename).suffix.lower() == ".svg":
        size = svg_text_size(data.decode())
        if not size:
            raise ValueError(f"{filename}: no size in its <svg>")

        w, h = ceil(size[0]), ceil(size[1])
        scale = min(SVG_SCALE, ceil(SVG_WIDTH / w))
        return (
            f"{stem}.png",
            "image/png",
            draw_svg(data.decode(), w, h, scale),
            w * scale,
            h * scale,
        )

    with Image.open(BytesIO(data)) as x:
        w, h = x.size
        # by what it holds: a GIF can sit in a .webp
        if x.format in ("PNG", "JPEG", "GIF"):
            return f"{stem}.{x.format.lower()}", Image.MIME[x.format], data, w, h

        out = BytesIO()
        x.save(out, "PNG")
        return f"{stem}.png", "image/png", out.getvalue(), w, h


# MARK: Medium

# the settings page's GraphQL, cut to what this needs
SET_TAGS = """mutation SetPostTagsMutation($targetPostId: ID!, $tagNames: [String!]!) {
  setPostTags(targetPostId: $targetPostId, tagNames: $tagNames) {
    tagsConnection { edges { node { displayTitle } } }
  }
}"""
SET_CANONICAL = """mutation UpdateCanonicalUrl($input: UpdateCanonicalUrlInput!) {
  updateCanonicalUrl(input: $input) { __typename }
}"""
# a story, as `mirrors.py` compares and counts it
STORY = """id title mediumUrl canonicalUrl
  firstPublishedAt latestPublishedAt isPublished hasUnpublishedEdits
  totalStats { views reads } clapCount postResponses { count }
  content { bodyModel { paragraphs { type text } } }"""
GET_STORY = f"""query PostQuery($id: ID!) {{ post(id: $id) {{ {STORY} }} }}"""
GET_STORIES = f"""query UserStoriesQuery($paging: PagingOptions) {{
  viewer {{
    homepagePostsConnection(paging: $paging) {{
      posts {{ {STORY} }}
      pagingInfo {{ next {{ from limit }} }}
    }}
  }}
}}"""
FIND_TAGS = """query TagsMultiSelectFieldQuery($prefix: String!, $includeNormalized: Boolean!) {
  tagsTypeahead(prefix: $prefix, includeNormalized: $includeNormalized) {
    displayTitle normalizedTagSlug followerCount postCount
  }
}"""


class Medium:
    """The web editor's endpoints, with the owner's login."""

    def __init__(self):
        cookies = json.loads(subprocess.check_output(UNJAR))
        jar = {x["name"]: x["value"] for x in cookies}
        # a visitor gets a `uid` too, one that starts with lo_
        if jar.get("uid", "lo_").startswith("lo_") or "xsrf" not in jar:
            raise RuntimeError(f"no Medium login in `{' '.join(UNJAR)}`: log in there first")

        self.xsrf = jar["xsrf"]  # the editor sends the same in a header
        self.http = requests.Session(impersonate="chrome", timeout=60)
        for x in cookies:
            self.http.cookies.set(x["name"], x["value"], domain=x["domain"], path=x["path"])

    def answer(self, path: str, rep: requests.Response) -> dict:
        try:
            rs = json.loads(rep.text.removeprefix(GUARD))
        except json.JSONDecodeError:
            raise RuntimeError(
                f"{path}: HTTP {rep.status_code}, not JSON: {rep.text[:200]}"
            ) from None

        if not rs.get("success"):
            raise RuntimeError(
                f"{path}: HTTP {rep.status_code}, {rs.get('error') or rep.text[:200]}"
            )

        return rs["payload"]

    def api(self, method: str, path: str, body: dict | None = None) -> dict:
        headers = {"accept": "application/json", "x-obvious-cid": "web", "x-xsrf-token": self.xsrf}
        headers["x-client-date"] = str(time.time_ns() // 1_000_000)
        return self.answer(
            path, self.http.request(method, MEDIUM + path, json=body, headers=headers)
        )

    def graphql(self, query: str, variables: dict) -> dict:
        op = re.search(r"(?:query|mutation) (\w+)", query)[1]
        pld = [{"operationName": op, "variables": variables, "query": query}]
        headers = {"apollographql-client-name": "lite", "graphql-operation": op}
        rep = self.http.post(f"{MEDIUM}/_/graphql", json=pld, headers=headers)
        rs = rep.json()[0]
        if rs.get("errors") or not rs.get("data"):
            raise RuntimeError(
                f"{op}: HTTP {rep.status_code}, {rs.get('errors') or rep.text[:200]}"
            )

        return rs["data"]

    def upload(self, filename: str, mime: str, data: bytes) -> str:
        form = CurlMime()
        form.addpart("uploadedFile", content_type=mime, filename=filename, data=data)
        headers = {"accept": "application/json", "x-obvious-cid": "web", "x-xsrf-token": self.xsrf}
        try:
            rep = self.http.post(f"{MEDIUM}/_/upload?source=6", multipart=form, headers=headers)
        finally:
            form.close()

        return self.answer("/_/upload", rep)["value"]["fileId"]

    def create(self) -> str:
        pld = {"deltas": [], "baseRev": -1, "coverless": True, "visibility": 0}
        return self.api("POST", "/new-story", pld)["value"]["id"]

    def state(self, pid: str) -> tuple[int, int, int]:
        """The story's latest revision, and how many paragraphs and sections it has: its deltas
        replayed from the start, fetched a page at a time, as the editor does."""
        rev, paras, sections = -1, 0, 0
        while rs := self.api("GET", f"/p/{pid}/deltas?baseRev={rev}")["postDeltas"]:
            for x in rs:
                match x["delta"]["type"]:
                    case 1:  # INSERT
                        paras += 1
                    case 2:  # DELETE
                        paras -= 1
                    case 3 | 4 | 5:  # UPDATE, and the card's title and subtitle
                        pass
                    case 8:  # SECTION
                        sections += 1
                    case 9:  # UNSECTION
                        sections -= 1
                    case 12:  # no content: where the story went out, as far as seen
                        pass
                    case _:
                        raise RuntimeError(f"{pid}: a delta of unknown kind: {x['delta']}")

            rev = rs[-1]["rev"]

        return rev, paras, sections

    def push(self, pid: str, rev: int, deltas: list[dict]) -> int:
        for k in range(0, len(deltas), CHUNK):
            pld = {"id": pid, "deltas": deltas[k : k + CHUNK], "baseRev": rev}
            rev = self.api("POST", f"/p/{pid}/deltas", pld)["value"]["latestRev"]

        return rev

    def canonical(self, pid: str, url: str) -> None:
        self.graphql(SET_CANONICAL, {"input": {"postId": pid, "url": url}})

    def set_tags(self, pid: str, tags: list[str]) -> list[str]:
        """Gives the tags Medium took."""
        rep = self.graphql(SET_TAGS, {"targetPostId": pid, "tagNames": tags})
        return [x["node"]["displayTitle"] for x in rep["setPostTags"]["tagsConnection"]["edges"]]

    def story(self, pid: str) -> dict | None:
        return self.graphql(GET_STORY, {"id": pid})["post"]

    def stories(self) -> list[dict]:
        """The owner's published stories, newest first."""
        rs, paging = [], {"limit": 25}
        while paging:
            rep = self.graphql(GET_STORIES, {"paging": paging})["viewer"]["homepagePostsConnection"]
            rs += rep["posts"]
            paging = rep["pagingInfo"]["next"]

        return rs

    def find_tags(self, prefix: str) -> list[dict]:
        """The tags the settings page offers for a prefix, most followed first."""
        rep = self.graphql(FIND_TAGS, {"prefix": prefix, "includeNormalized": False})
        return sorted(rep["tagsTypeahead"], key=lambda x: -x["followerCount"])


# MARK: Main


def load_drafts() -> dict[str, str]:
    return json.loads(DRAFTS.read_text()) if DRAFTS.exists() else {}


def save_draft(slug: str, pid: str) -> None:
    rs = load_drafts() | {slug: pid}
    DRAFTS.parent.mkdir(parents=True, exist_ok=True)
    DRAFTS.write_text(json.dumps(rs, indent=2, sort_keys=True) + "\n")


def section(index: int, start: int) -> dict:
    return {"type": SECTION, "index": index, "section": {"name": name(), "startIndex": start}}


def upload_images(post: Post, doc: list[dict], medium: Medium) -> None:
    done = {}  # src -> metadata: the same picture twice goes up once
    for x in doc:
        if x["type"] != IMG:
            continue

        src, alt = x.pop("src"), x.pop("alt")
        if src not in done:
            filename, mime, data, w, h = raster(*image_file(src, post))
            file_id = medium.upload(filename, mime, data)
            done[src] = {"id": file_id, "originalWidth": w, "originalHeight": h}
            print(f"  {src[:60]} -> {file_id}")

        x["metadata"] = done[src] | {"alt": alt}


def publish(post: Post, pid: str | None, tags: list[str] | None, medium: Medium) -> str:
    """Tags are set when given, and else only on a new draft, from the post: Medium's own may be
    better ones, picked by --find, or by hand."""
    doc, breaks = convert(post)
    upload_images(post, doc, medium)

    rev, old, sections = medium.state(pid) if pid else (-1, 0, 0)
    if not pid:
        pid = medium.create()
        save_draft(post.slug, pid)  # before anything else can fail

    deltas = [] if sections else [section(0, 0)]
    # every section but the first goes, and the post's own come back after the text
    deltas += [{"type": UNSECTION, "index": k} for k in range(sections - 1, 0, -1)]
    deltas += [{"type": INSERT, "index": k, "paragraph": x} for k, x in enumerate(doc)]
    # what was there before sits after the new text now
    deltas += [{"type": DELETE, "index": len(doc)} for _ in range(old)]
    deltas += [section(k + 1, at) for k, at in enumerate(breaks)]
    medium.push(pid, rev, deltas)
    medium.canonical(pid, SITE + post.url)

    if tags is None and rev < 0:
        tags = post.tags
    if tags is not None:
        if len(tags) > TAGS_MAX:
            warn(f"Medium takes {TAGS_MAX} tags, left out: {', '.join(tags[TAGS_MAX:])}")
        print(f"  tags: {', '.join(medium.set_tags(pid, tags[:TAGS_MAX]))}")

    _, paras, sections = medium.state(pid)
    want = len(doc), len(breaks) + 1
    if (paras, sections) != want:
        warn(f"{pid} has {paras} paragraphs in {sections} sections, not {want[0]} in {want[1]}")

    if (x := medium.story(pid))["isPublished"] and x["hasUnpublishedEdits"]:
        print("  published: Medium keeps the change aside till Save and publish in its editor")

    return pid


def dry(post: Post) -> None:
    doc, breaks = convert(post)
    for k, x in enumerate(doc):
        if k in breaks:
            print("---")
        kind = KINDS[x["type"]]
        text = x.get("src") or x["text"].replace("\n", "⏎")
        marks = " ".join(f"{m['type']}:{m['start']}-{m['end']}" for m in x["markups"])
        print(f"{kind:4} {text[:90]}" + (f"  [{marks}]" if marks else ""))


def main() -> None:
    cli = argparse.ArgumentParser(description="Push a post to Medium as a draft.")
    cli.add_argument("slug", nargs="?")
    cli.add_argument("--id", help="the Medium story to update: its id or URL")
    cli.add_argument("--new", action="store_true", help="make a new draft even if one exists")
    cli.add_argument("--tags", help="Medium's tags, by commas; a new draft takes the post's own")
    cli.add_argument("--find", nargs="+", metavar="WORD", help="list Medium's tags for each word")
    cli.add_argument("--dry", action="store_true", help="print the paragraphs, touch nothing")
    args = cli.parse_args()

    if args.find:
        # readers a tag has, and how many stories they share them with
        medium = Medium()
        rs = {x["normalizedTagSlug"]: x for word in args.find for x in medium.find_tags(word)}
        print(f"{'followers':>11} {'stories':>11} {'per story':>9}  tag")
        for x in sorted(rs.values(), key=lambda x: -x["followerCount"]):
            rate = x["followerCount"] / max(x["postCount"], 1)
            print(
                f"{x['followerCount']:>11,} {x['postCount']:>11,} {rate:>9.2f}  {x['displayTitle']}"
            )
        return

    if not args.slug:
        cli.error("a slug, or --find")

    post = read_posts(drafts=True).get((args.slug, "en"))
    if not post:
        sys.exit(f"medium: no post {args.slug} in English")

    if args.dry:
        dry(post)
        return

    pid = None
    if args.id:
        m = POST_ID.search(args.id)
        if not m:
            sys.exit(f"medium: no story id in {args.id}")
        pid = m[1]
    elif post.medium and not args.new:
        sys.exit(f"medium: {post.slug} is out on Medium already, {post.medium}: pass --id or --new")
    elif not args.new:
        pid = load_drafts().get(post.slug)

    tags = [x.strip() for x in args.tags.split(",")] if args.tags else None
    pid = publish(post, pid, tags, Medium())

    print(f"{MEDIUM}/p/{pid}/edit")


if __name__ == "__main__":
    main()
