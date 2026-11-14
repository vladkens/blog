"""The blog's copies on Medium and dev.to, and how they stand: for each post, whether its copy on
each site points back here, whether its text is still the post's, and how it is read. `medium.py`
and `devto.py` make and update the copies; this finds what needs them.

Each `stats` run is kept in STATS, so the counts add up to a history and the table shows what
changed since the run before.

  kc run -- uv run python scripts/mirrors.py                      # the copies, and what is off
  kc run -- uv run python scripts/mirrors.py stats                # their counts, kept
  kc run -- uv run python scripts/mirrors.py canonical            # copies that don't point here
  kc run -- uv run python scripts/mirrors.py canonical --apply    # point them here
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import devto
import medium

from content import Post, read_posts

SITE = "https://vladkens.me"
SITES = {"medium": "Medium", "devto": "dev.to"}
# one line per `stats` run: when, and every copy's counts
STATS = Path.home() / ".local" / "share" / "vladkens.me" / "mirrors.jsonl"

# what tells two texts apart only in typography
SPACES = re.compile(r"\s+")  # a hair or no-break space too
QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


@dataclass
class Copy:
    site: str
    id: str
    url: str
    title: str
    published: date | None  # None for a draft
    canonical: str | None  # None when it is the copy's own address
    text: list[str]
    views: int
    reads: int | None  # Medium's: views read through
    reactions: int
    comments: int
    slug: str | None = None  # the post it copies


def norm(lines: list[str]) -> list[str]:
    rs = (SPACES.sub(" ", x.translate(QUOTES)).strip() for x in lines)
    return [x for x in rs if x]


# MARK: Sites


def medium_copy(x: dict) -> Copy:
    at = x["firstPublishedAt"]
    return Copy(
        site="medium",
        id=x["id"],
        url=x["mediumUrl"],
        title=x["title"],
        published=datetime.fromtimestamp(at / 1000, UTC).date() if at else None,
        canonical=x["canonicalUrl"] if x["canonicalUrl"] != x["mediumUrl"] else None,
        text=norm(
            [p["text"] for p in x["content"]["bodyModel"]["paragraphs"] if p["type"] != "IMG"]
        ),
        views=x["totalStats"]["views"],
        reads=x["totalStats"]["reads"],
        reactions=x["clapCount"],
        comments=x["postResponses"]["count"],
    )


def devto_copy(x: dict) -> Copy:
    own = x["canonical_url"].startswith("https://dev.to/")
    return Copy(
        site="devto",
        id=str(x["id"]),
        url=x["url"],
        title=x["title"],
        published=date.fromisoformat(x["published_at"][:10]) if x["published"] else None,
        canonical=None if own else x["canonical_url"],
        text=norm(x["body_markdown"].splitlines()),
        views=x["page_views_count"],
        reads=None,
        reactions=x["public_reactions_count"],
        comments=x["comments_count"],
    )


def local_text(site: str, post: Post) -> list[str]:
    """The post as the site would get it now."""
    if site == "medium":
        return norm([x["text"] for x in medium.convert(post)[0] if x["type"] != medium.IMG])

    return norm(devto.convert(post)[0].splitlines())


def copies(posts: list[Post]) -> list[Copy]:
    """Every copy on both sites, each with the post it copies when one does."""
    md = medium.Medium()
    stories = {x["id"]: x for x in md.stories()}
    drafts = medium.load_drafts()
    for pid in set(drafts.values()) - set(stories):
        if x := md.story(pid):
            stories[pid] = x

    key = os.environ.get("DEVTO_API_KEY")
    if not key:
        sys.exit(
            "mirrors: no DEVTO_API_KEY: run it as `kc run -- uv run python scripts/mirrors.py`"
        )

    rs = [medium_copy(x) for x in stories.values()]
    rs += [devto_copy(x) for x in devto.DevTo(key).articles()]

    def owns(post: Post, x: Copy) -> bool:
        if x.canonical == SITE + post.url:
            return True
        if x.site == "devto":
            return x.url == post.devto
        m = medium.POST_ID.search(post.medium or "")
        return x.id == (m[1] if m else drafts.get(post.slug))

    for post in posts:
        for x in rs:
            if not x.slug and owns(post, x):
                x.slug = post.slug

    return rs


# MARK: Commands


def status(posts: list[Post], rs: list[Copy]) -> None:
    """A copy is off when it points elsewhere, when its text is not the post's of today, or when
    the post changed after the copy went out."""
    print(f"{'post':<40} {'Medium':<26} dev.to")
    for post in posts:
        cells = []
        for site in SITES:
            x = next((x for x in rs if x.slug == post.slug and x.site == site), None)
            if not x:
                cells.append("—")
                continue

            same = SequenceMatcher(None, x.text, local_text(site, post)).ratio()
            flags = ["out" if x.published else "draft", f"{same:4.0%}"]
            flags += [] if x.canonical == SITE + post.url else ["no canonical"]
            flags += ["post newer"] if x.published and post.modified > x.published else []
            cells.append(" ".join(flags))

        print(f"{post.slug[:40]:<40} {cells[0]:<26} {cells[1]}")

    if lost := [x for x in rs if not x.slug]:
        print("\nno post here:")
        for x in lost:
            print(f"  {SITES[x.site]:<7} {x.title[:60]:<60} {x.url}")


def stats(rs: list[Copy]) -> None:
    last = {}
    if STATS.exists():
        lines = STATS.read_text().splitlines()
        last = {(x["site"], x["id"]): x for x in json.loads(lines[-1])["copies"]} if lines else {}

    def cell(x: Copy, field: str) -> str:
        now, before = getattr(x, field), last.get((x.site, x.id), {}).get(field)
        if now is None:
            return ""
        return f"{now:,}" + (f" +{now - before:,}" if before is not None and now > before else "")

    rs = sorted(rs, key=lambda x: -x.views)
    print(f"{'site':<7} {'views':>13} {'reads':>11} {'reactions':>9} {'comments':>8}  title")
    for x in rs:
        row = [cell(x, k) for k in ("views", "reads", "reactions", "comments")]
        print(
            f"{SITES[x.site]:<7} {row[0]:>13} {row[1]:>11} {row[2]:>9} {row[3]:>8}  {x.title[:50]}"
        )

    for site, title in SITES.items():
        print(f"{title}: {sum(x.views for x in rs if x.site == site):,} views in all")

    keep = ("site", "id", "slug", "views", "reads", "reactions", "comments")
    at = datetime.now(UTC).isoformat(timespec="seconds")
    pld = {"at": at, "copies": [{k: v for k, v in asdict(x).items() if k in keep} for x in rs]}
    STATS.parent.mkdir(parents=True, exist_ok=True)
    with STATS.open("a") as f:
        f.write(json.dumps(pld) + "\n")


def canonical(posts: list[Post], rs: list[Copy], apply: bool) -> None:
    urls = {x.slug: SITE + x.url for x in posts}
    off = [x for x in rs if x.slug and x.canonical != urls[x.slug]]
    if not off:
        print("every copy points here")
        return

    key = os.environ.get("DEVTO_API_KEY")
    md, dt = (medium.Medium(), devto.DevTo(key)) if apply else (None, None)
    for x in off:
        print(f"{SITES[x.site]:<7} {x.slug:<40} {x.canonical or 'its own'} -> {urls[x.slug]}")
        if not apply:
            continue

        if x.site == "medium":
            md.canonical(x.id, urls[x.slug])
        else:
            dt.call("PUT", f"/articles/{x.id}", {"article": {"canonical_url": urls[x.slug]}})

    if not apply:
        print("\npass --apply to set them")


def main() -> None:
    cli = argparse.ArgumentParser(description="The blog's copies on Medium and dev.to.")
    cli.add_argument(
        "command", nargs="?", default="status", choices=["status", "stats", "canonical"]
    )
    cli.add_argument("--apply", action="store_true", help="canonical: set it on each copy")
    args = cli.parse_args()

    posts = read_posts(drafts=False)
    posts = sorted(
        (x for x in posts.values() if x.lang == "en"), key=lambda x: x.date, reverse=True
    )
    rs = copies(posts)
    match args.command:
        case "status":
            status(posts, rs)
        case "stats":
            stats(rs)
        case "canonical":
            canonical(posts, rs, args.apply)


if __name__ == "__main__":
    main()
