import re
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit

from app import BASE_URL, app, og_path, redirects, unlisted_urls
from content import ROOT, srcset_urls

PUBLIC = ROOT / "public"
START = ["/", "/ru/", "/404.html", "/ru/404.html", "/sitemap.xml"]
START += [f"{x}{y}.xml" for x in ("/", "/ru/") for y in ("atom", "rss")]

# Nothing links to these: they are asked for by name
START += ["/ssh", "/robots.txt", "/favicon.ico"]

CSS_URL = re.compile(r"""url\(\s*["']?([^"')\s]+)""")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        self.urls += [v for k, v in attrs if k in ("href", "src", "data-src") and v]
        if tag == "meta" and {("property", "og:image"), ("name", "twitter:image")} & set(attrs):
            self.urls.append(dict(attrs)["content"])

        self.urls += [x for k, v in attrs if k == "srcset" and v for x in srcset_urls(v)]
        self.ids |= {v for k, v in attrs if k == "id" and v}


def internal_path(url: str, page: str) -> str | None:
    x = urlsplit(urljoin(page, url))
    if x.scheme not in ("", "http", "https"):
        return None

    if x.netloc and x.netloc != urlsplit(BASE_URL).netloc:
        return None

    return unquote(x.path) or "/"


def xml_urls(data: bytes) -> list[str]:
    """What the sitemap or a feed points at, the links inside a feed's posts too. A feed that isn't
    well-formed stops the build here."""
    urls = []
    for x in ET.fromstring(data).iter():
        name = x.tag.rpartition("}")[2]
        if name in ("loc", "guid") or (name == "link" and x.text):
            urls.append(x.text)

        if name == "link" and x.get("href"):
            urls.append(x.get("href"))

        if name in ("content", "description"):
            parser = Links()
            parser.feed(x.text)
            urls += parser.urls

    return urls


def write(path: str, data: bytes) -> None:
    target = PUBLIC / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def write_redirects() -> None:
    """Cloudflare Pages reads public/_redirects: `source destination code`, one to a line, up to 2,000
    static ones, and it runs them ahead of any file. Its docs don't say that a source matches with
    and without the slash, so each form gets its own line.
    https://developers.cloudflare.com/pages/configuration/redirects/"""
    rows = [
        f"{x} {new} 301"
        for old, new in redirects().items()
        for x in dict.fromkeys((old.rstrip("/"), old))
    ]
    (PUBLIC / "_redirects").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_headers(urls: list[str]) -> None:
    """Cloudflare Pages reads public/_headers: a path, then its headers indented under it, up to 100
    rules. An unlisted post asks search engines to leave it out: its page, what sits under it, its
    images, and its card. The docs don't say that `*` matches nothing, so the page has its own
    rule; where both match, the values join as `noindex, noindex`, which reads the same. robots.txt
    leaves it alone: a crawler it turns away never reads this.
    https://developers.cloudflare.com/pages/configuration/headers/"""
    paths = [x for url in urls for x in (url, f"{url}*", og_path(url))]
    rows = [f"{x}\n  X-Robots-Tag: noindex" for x in paths]
    if rows:
        (PUBLIC / "_headers").write_text("\n".join(rows) + "\n", encoding="utf-8")


def freeze(start: list[str]) -> dict[str, set[str]]:
    """Writes public/, returns broken internal URLs with the pages linking to them."""
    client = app.test_client()
    queue = deque(start)
    seen = set(start)
    sources = defaultdict(set)
    ids = {}
    anchors = defaultdict(set)
    broken = {}

    def follow(url: str, page: str) -> None:
        target = internal_path(url, page)
        if target is None:
            return

        fragment = unquote(urlsplit(url).fragment)
        if fragment:
            anchors[target, fragment].add(page)

        sources[target].add(page)
        if target not in seen:
            seen.add(target)
            queue.append(target)

    # where a redirect lands is held to the same rules as a link
    for new in redirects().values():
        follow(new, "_redirects")

    while queue:
        path = queue.popleft()
        rep = client.get(path)
        rep.direct_passthrough = False

        if rep.status_code != 200:
            broken[path] = sources[path]
            continue

        write(path, rep.get_data())

        urls = []
        if rep.mimetype == "text/css":
            urls = CSS_URL.findall(rep.get_data(as_text=True))

        if rep.mimetype == "text/html":
            parser = Links()
            parser.feed(rep.get_data(as_text=True))
            ids[path] = parser.ids
            urls = parser.urls

        if rep.mimetype.endswith("xml"):
            urls = xml_urls(rep.get_data())

        for url in urls:
            follow(url, path)

    print(f"{len(seen) - len(broken)} URLs written to {PUBLIC.name}/")

    for (target, fragment), pages in anchors.items():
        if target in ids and fragment not in ids[target]:
            broken[f"{target}#{fragment}"] = pages

    return broken


def main() -> None:
    app.config["DRAFTS"] = "--drafts" in sys.argv
    app.testing = True  # a render error stops the build with its message

    shutil.rmtree(PUBLIC, ignore_errors=True)
    PUBLIC.mkdir()
    write_redirects()

    # nothing links to an unlisted post
    with app.app_context():
        unlisted = unlisted_urls()

    write_headers(unlisted)

    broken = freeze(START + unlisted)
    for url, pages in sorted(broken.items()):
        print(f"broken: {url} <- {', '.join(sorted(pages))}", file=sys.stderr)

    if broken:
        sys.exit(1)


if __name__ == "__main__":
    main()
