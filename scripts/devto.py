"""Pushes a post's English version to dev.to: a new unpublished article, or the one that already
points to the post, with its text replaced. dev.to has an API for this and takes Markdown, so the
post's own goes: its addresses in full, its headings a level down, as on the site. Its pictures
stay on the site, so the post goes out there first, except SVGs: dev.to shows none, so each is
drawn to PNG as for Medium and goes up to dev.to's own storage, by the editor's upload with the
owner's login from Helium by unjar.

The API key is DEVTO_API_KEY, from the Keychain by kc.

  kc run -- uv run python scripts/devto.py <slug>                 # create the article, or update it
  kc run -- uv run python scripts/devto.py <slug> --live          # update it even when published
  kc run -- uv run python scripts/devto.py <slug> --tags rust,ai  # set dev.to's tags
  kc run -- uv run python scripts/devto.py --find rust ai         # dev.to's tags, by popularity
  uv run python scripts/devto.py <slug> --dry                     # print the Markdown, send nothing
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from curl_cffi import CurlMime, requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import medium

from content import Post, describe, read_posts

SITE = "https://vladkens.me"
DEVTO = "https://dev.to"
API = f"{DEVTO}/api"
# the owner's dev.to cookies, for the upload the API lacks
UNJAR = ["unjar", "-b", "helium", "-f", "json", "dev.to"]

# what goes under every article, in Markdown as a post; no file, no footer
FOOTER = ROOT / "assets" / "mirrors" / "devto.md"

# an article takes this many tags at most, each of letters and digits only
TAGS_MAX = 4

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
CODE_SPAN = re.compile(r"(`+).+?\1")
MD_URL = re.compile(r"(!?\[[^\]]*\]\()(<[^>]*>|[^)\s]+)")  # a link or a picture, and its address
HTML_URL = re.compile(r"""(\b(?:src|href)\s*=\s*["'])([^"']*)""", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,5}) ")
SVG_OPEN, SVG_CLOSE = re.compile(r"^\s*<svg\b", re.IGNORECASE), re.compile(r"</svg>", re.IGNORECASE)


def warn(msg: str) -> None:
    print(f"devto: {msg}", file=sys.stderr)


# MARK: Markdown


def full(url: str, base: str) -> str:
    """An address as a reader away from the site needs it; an anchor stays in the article."""
    if url.startswith("#") or urlsplit(url).scheme:
        return url

    return urljoin(base, url)


def outside_code(line: str, fn) -> str:
    """`fn` on the line's text, not on its code spans."""
    rs, at = [], 0
    for m in CODE_SPAN.finditer(line):
        rs += [fn(line[at : m.start()]), m[0]]
        at = m.end()

    return "".join([*rs, fn(line[at:])])


def inline_svg(lines: list[str], images: list[str]) -> str:
    x = medium.svg_image("\n".join(lines))
    images.append(x["src"])
    return f"![{x['alt']}]({x['src']})"


def convert(post: Post) -> tuple[str, list[str]]:
    """The body for dev.to, and the pictures it shows: from the site, or inline SVGs as data:
    URLs."""
    base = SITE + post.url
    images = []

    def addresses(text: str) -> str:
        def link(m: re.Match) -> str:
            url = full(m[2].strip("<>"), base)
            if m[1].startswith("!"):
                images.append(url)
            return m[1] + url

        def attr(m: re.Match) -> str:
            url = full(m[2], base)
            if m[1].lower().startswith("src"):
                images.append(url)
            return m[1] + url

        return HTML_URL.sub(attr, MD_URL.sub(link, text))

    rs, fence, svg = [], None, None
    body = post.body.rstrip() + ("\n\n" + FOOTER.read_text() if FOOTER.exists() else "")
    for line in body.splitlines():
        if svg is not None:
            svg.append(line)
            if SVG_CLOSE.search(line):
                rs.append(inline_svg(svg, images))
                svg = None
            continue

        if m := FENCE.match(line):
            if not fence:
                fence = m[1]
            elif m[1].startswith(fence):
                fence = None
            rs.append(line)
            continue

        if fence:
            rs.append(line)
            continue

        if SVG_OPEN.match(line):
            # dev.to keeps no <svg>: it goes as a picture, drawn and uploaded by push()
            svg = [line]
            if SVG_CLOSE.search(line):
                rs.append(inline_svg(svg, images))
                svg = None
            continue

        # the title is the article's h1, so the body's headings go a level down, as on the site
        line = HEADING.sub(r"#\1 ", line)
        rs.append(outside_code(line, addresses))

    return "\n".join(rs).strip() + "\n", images


# MARK: dev.to


class DevTo:
    def __init__(self, key: str | None):
        # Forem's v1 needs its own accept, and some of its answers a browser's TLS
        headers = {"accept": "application/vnd.forem.api-v1+json"}
        self.http = requests.Session(impersonate="chrome", timeout=60, headers=headers)
        if key:
            self.http.headers["api-key"] = key

    def call(self, method: str, path: str, body: dict | None = None):
        rep = self.http.request(method, API + path, json=body)
        # dev.to lets a few edits through in a row, then asks to wait
        for _ in range(5):
            if rep.status_code != 429:
                break
            time.sleep(int(rep.headers.get("retry-after") or 30))
            rep = self.http.request(method, API + path, json=body)

        if rep.status_code >= 400:
            raise RuntimeError(f"{method} {path}: HTTP {rep.status_code}, {rep.text[:300]}")

        return rep.json()

    def find(self, post: Post) -> dict | None:
        """The article already made for the post: by its canonical address, or the one the post
        names in `devto`."""
        rs = self.articles()
        return next((x for x in rs if SITE + post.url == x["canonical_url"]), None) or next(
            (x for x in rs if post.devto and x["url"] == post.devto), None
        )

    def articles(self) -> list[dict]:
        """The owner's articles, drafts too, with their text and counts."""
        return self.call("GET", "/articles/me/all?per_page=1000")

    def tags(self) -> list[str]:
        """dev.to's top tags, the most popular first."""
        return [x["name"] for x in self.call("GET", "/tags?per_page=1000")]


def clean_tags(tags: list[str]) -> list[str]:
    rs = list(dict.fromkeys(re.sub(r"[^a-z0-9]", "", x.lower()) for x in tags))
    if len(rs) > TAGS_MAX:
        warn(f"dev.to takes {TAGS_MAX} tags, left out: {', '.join(rs[TAGS_MAX:])}")

    return [x for x in rs[:TAGS_MAX] if x]


class Uploads:
    """dev.to's own picture storage, as its editor uploads to it: the API has no way in."""

    def __init__(self):
        cookies = json.loads(subprocess.check_output(UNJAR))
        self.http = requests.Session(impersonate="chrome", timeout=60)
        for x in cookies:
            self.http.cookies.set(x["name"], x["value"], domain=x["domain"], path=x["path"])

        # the pages fill their CSRF token in from here, with whom it is for
        rs = self.http.get(f"{DEVTO}/async_info/base_data", headers={"accept": "application/json"})
        rs = rs.json()
        if not rs.get("user") or not rs.get("token"):
            raise RuntimeError(f"no dev.to login in `{' '.join(UNJAR)}`: log in there first")
        self.csrf = rs["token"]

    def upload(self, filename: str, mime: str, data: bytes) -> str:
        form = CurlMime()
        form.addpart("image[]", content_type=mime, filename=filename, data=data)
        headers = {"accept": "application/json", "x-csrf-token": self.csrf}
        try:
            rep = self.http.post(f"{DEVTO}/image_uploads", multipart=form, headers=headers)
        finally:
            form.close()

        if rep.status_code >= 400:
            raise RuntimeError(f"upload {filename}: HTTP {rep.status_code}, {rep.text[:300]}")
        return rep.json()["links"][0]


def is_svg(url: str) -> bool:
    return url.startswith("data:image/svg") or urlsplit(url).path.lower().endswith(".svg")


def upload_svgs(post: Post, body: str, images: list[str]) -> str:
    """Each SVG drawn to PNG and uploaded, its address in the body swapped for the upload's."""
    svgs = list(dict.fromkeys(x for x in images if is_svg(x)))
    if not svgs:
        return body

    up = Uploads()
    for src in svgs:
        # the site's own SVG is read from the repo, as the site has it
        name = urlsplit(src).path if src.startswith(SITE) else src
        url = up.upload(*medium.raster(*medium.image_file(name, post))[:3])
        print(f"  {src[:60]} -> {url}")
        body = body.replace(f"]({src})", f"]({url})").replace(f'="{src}"', f'="{url}"')

    return body


def missing(urls: list[str]) -> list[str]:
    http = requests.Session(impersonate="chrome", timeout=30)
    return [x for x in dict.fromkeys(urls) if http.head(x, allow_redirects=True).status_code != 200]


# MARK: Main


def push(post: Post, tags: list[str] | None, live: bool, new: bool, devto: DevTo) -> str:
    body, images = convert(post)
    if gone := missing([x for x in images if x.startswith(SITE) and not is_svg(x)]):
        raise RuntimeError(f"not on the site yet, deploy it first: {', '.join(gone)}")

    article = {"title": post.title, "body_markdown": body, "canonical_url": SITE + post.url}
    # no cover: dev.to cuts any picture to 1000x420, and the OG card loses its top
    article["description"] = describe(post)

    old = None if new else devto.find(post)
    if old and old["published"] and not live:
        raise RuntimeError(f"{old['url']} is published: pass --live to replace its text")

    article["body_markdown"] = upload_svgs(post, body, images)

    if tags is not None or not old:
        article["tags"] = clean_tags(post.tags if tags is None else tags)

    if old:
        rs = devto.call("PUT", f"/articles/{old['id']}", {"article": article})
    else:
        rs = devto.call("POST", "/articles", {"article": article | {"published": False}})

    # a string here, though the API gives a list elsewhere
    tags = rs["tag_list"]
    print(f"  tags: {tags if isinstance(tags, str) else ', '.join(tags)}")
    return rs["url"]


def main() -> None:
    cli = argparse.ArgumentParser(description="Push a post to dev.to as an unpublished article.")
    cli.add_argument("slug", nargs="?")
    cli.add_argument("--tags", help="dev.to's tags, by commas; a new article takes the post's own")
    cli.add_argument("--live", action="store_true", help="replace a published article's text")
    cli.add_argument("--new", action="store_true", help="make a new article even if one exists")
    cli.add_argument("--find", nargs="+", metavar="WORD", help="list dev.to's tags for each word")
    cli.add_argument("--dry", action="store_true", help="print the Markdown, send nothing")
    args = cli.parse_args()

    if args.find:
        for k, x in enumerate(DevTo(None).tags(), 1):
            if any(w.lower() in x for w in args.find):
                print(f"{k:>5}  {x}")
        return

    if not args.slug:
        cli.error("a slug, or --find")

    post = read_posts(drafts=True).get((args.slug, "en"))
    if not post:
        sys.exit(f"devto: no post {args.slug} in English")

    if args.dry:
        print(re.sub(r"\(data:[^)]{40}[^)]*\)", "(data:…)", convert(post)[0]), end="")
        return

    key = os.environ.get("DEVTO_API_KEY")
    if not key:
        sys.exit(
            "devto: no DEVTO_API_KEY: run it as `kc run -- uv run python scripts/devto.py ...`"
        )

    tags = [x.strip() for x in args.tags.split(",")] if args.tags else None
    print(push(post, tags, args.live, args.new, DevTo(key)))


if __name__ == "__main__":
    main()
