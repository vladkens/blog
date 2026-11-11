import hashlib
import os
import re
from contextlib import suppress
from datetime import UTC, date, datetime
from email.utils import format_datetime
from functools import cache
from zlib import crc32

from flask import (
    Flask,
    Response,
    abort,
    g,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
)
from werkzeug.security import safe_join

from content import (
    APPS_DIR,
    PAGES_DIR,
    POSTS_DIR,
    SRC,
    STATIC_DIR,
    Apps,
    Doc,
    Docs,
    Posts,
    absolute_html,
    app_posts,
    describe,
    list_posts,
    list_tags,
    page_url,
    read_apps,
    read_pages,
    read_posts,
    render,
    tag_url,
    toc,
)
from og import Card, draw_card

BASE_URL = "https://vladkens.me"
SITE = "vladkens.me"
REPO = "vladkens/blog"
LANGS = ("en", "ru")
LOCALES = {"en": "en_US", "ru": "ru_RU"}

# Who writes the site, in each page's structured data for search engines
AUTHOR = {
    "@type": "Person",
    "@id": f"{BASE_URL}/about/#person",
    "name": "vladkens",
    "url": f"{BASE_URL}/about/",
    "sameAs": ["https://github.com/vladkens", "https://x.com/uid127"],
}

# Images that lived at the root until posts got folders: <post>/<file>, once at /<file>
MOVED_IMAGES = [
    "2024-in-review/2024-review-dalle.webp",
    "2025-in-review/20251231.webp",
    "aws-ecs-cluster/aws-ecs-cluster-1.png",
    "aws-ecs-cluster/aws-ecs-cluster-2.png",
    "aws-ecs-cluster/aws-ecs-cluster-3.png",
    "aws-python-lambda/aws-python-lambda-cli.png",
    "coding-agents-statusline/20260521-0.png",
    "coding-agents-statusline/20260521-1.png",
    "deploy-fastapi-with-sqlite-on-flyio/sqlite-flyio.png",
    "fast-multi-arch-docker-for-rust/rust-docker-build-cover.png",
    "from-iterm-to-wezterm/20250109-0.png",
    "from-iterm-to-wezterm/20250109-1.png",
    "from-iterm-to-wezterm/20250109-2.png",
    "macmon/macmon-1.png",
    "macmon/macmon-2.webp",
    "og-image-generator/ogi-image-generator-1.png",
    "og-image-generator/ogi-image-generator-2.png",
    "rmd160-simd/20250508.png",
]

# old address -> new one; a renamed post's come from its `aliases`, see redirects()
REDIRECTS = {
    "/donate/": "/about/#support",
    "/ai-usage/": "/about/",
    **{f"/{x.rpartition('/')[2]}": f"/{x}" for x in MOVED_IMAGES},
}

FEEDS = {"atom": "application/atom+xml", "rss": "application/rss+xml"}

STRINGS = {
    "en": {
        "posts": "Posts",
        "apps": "Apps",
        "nav_blog": "blog",
        "nav_apps": "apps",
        "nav_about": "about",
        "nav_tags": "tags",
        "tags": "Tags",
        "tagged": "Posts tagged {}",
        "post_forms": ("post", "posts", "posts"),
        "blog_posts": "Blog posts",
        "stars": "GitHub stars",
        "descr": "Practical software engineering",
        "minutes": "{} min read",
        "reading_time": "Reading time",
        "markdown": "Markdown",
        "edit": "Edit",
        "not_found": "Nothing here :(",
        "footer": "All rights reserved. Code samples are public domain unless otherwise noted.",
        "built": "Built on",
        "commit": "commit",
        "toc": "Contents",
    },
    "ru": {
        "posts": "Посты",
        "apps": "Проекты",
        "nav_blog": "блог",
        "nav_apps": "проекты",
        "nav_about": "обо мне",
        "nav_tags": "теги",
        "tags": "Теги",
        "tagged": "Посты с тегом {}",
        "post_forms": ("пост", "поста", "постов"),
        "blog_posts": "Посты в блоге",
        "stars": "Звёзды на GitHub",
        "descr": "Практическая программная инженерия",
        "minutes": "{} мин чтения",
        "reading_time": "Время чтения",
        "markdown": "Markdown",
        "edit": "Редактировать",
        "not_found": "Здесь ничего нет :(",
        "footer": "Все права защищены. Примеры кода — общественное достояние, если не указано иное.",
        "built": "Собрано",
        "commit": "коммит",
        "toc": "Содержание",
    },
}

# The one work in the left field, a demo until the artist's page: static/ink-<name>.webp and -dark.webp,
# made by scripts/make-ink.py. `size` is the file's, `rows` its height where the field holds it whole.
WORK = {
    "name": "roadworks",
    "size": (448, 448),
    "rows": 7,
    "en": "Ink painting: a road sign, a man digging beside a mound of earth.",
    "ru": "Рисунок тушью: дорожный знак, человек копает рядом с кучей земли.",
}

# What sits beside the public files but is never one of them: dotfiles and Markdown sources
MARKDOWN = (".md", ".markdown")

app = Flask(__name__, static_folder=None)
app.config["DRAFTS"] = False

read_cached = cache(read_posts)
read_apps_cached = cache(read_apps)
read_pages_cached = cache(read_pages)


def private(name: str) -> bool:
    return name.startswith(".") or name.lower().endswith(MARKDOWN)


def get_posts() -> Posts:
    if app.debug:
        return read_posts(drafts=True)

    return read_cached(app.config["DRAFTS"])


def get_apps() -> Apps:
    return read_apps() if app.debug else read_apps_cached()


def get_pages() -> Docs[Doc]:
    return read_pages() if app.debug else read_pages_cached()


def unlisted_slugs() -> set[str]:
    """Posts shared by their link alone: one language marked unlisted takes the other with it. A
    draft's flag counts for nothing, on the dev server too: the build never has it. Once a request."""
    if "unlisted" not in g:
        g.unlisted = {x.slug for x in get_posts().values() if x.unlisted and not x.draft}

    return g.unlisted


def unlisted_urls() -> list[str]:
    """Pages nothing on the site links to: the build starts from them, and asks search engines to
    leave them out."""
    slugs = unlisted_slugs()
    return sorted(x.url for x in get_posts().values() if x.slug in slugs)


def listed_posts() -> Posts:
    """What the site's lists, tags and app pages show: an unlisted post is only at its address."""
    slugs = unlisted_slugs()
    return {k: x for k, x in get_posts().items() if x.slug not in slugs}


def public_posts() -> Posts:
    """Drafts show on the dev server and in a draft build, never in what others subscribe to."""
    return {k: x for k, x in listed_posts().items() if not x.draft}


def site_urls() -> set[str]:
    """Every page a link in Markdown can point at, in each language it has."""
    docs = [*get_posts().values(), *get_apps().values(), *get_pages().values()]
    tags = {tag_url(tag, x) for x in LANGS for tag in list_tags(listed_posts(), x)}
    return {x.url for x in docs} | tags | {page_url(y, x) for x in LANGS for y in ("apps", "tags")}


def home_url(lang: str) -> str:
    return f"/{lang}/" if lang != "en" else "/"


app.add_template_global(tag_url)


@app.template_global()
def asset(name: str) -> str:
    data = (STATIC_DIR / name).read_bytes()
    return f"/{name}?h={hashlib.sha256(data).hexdigest()[:8]}"


@app.template_filter()
def grouped(n: int, lang: str) -> str:
    return f"{n:,}".replace(",", "\u00a0" if lang == "ru" else ",")


@app.template_filter()
def atom_date(x: date) -> str:
    return f"{x}T00:00:00+00:00"


@app.template_filter()
def rss_date(x: date) -> str:
    return format_datetime(datetime(x.year, x.month, x.day, tzinfo=UTC))


@app.template_filter()
def keep_numbered(text: str) -> str:
    """A word joiner, so a line never breaks inside "RIPEMD-160"."""
    return re.sub(r"(?<=\w)-(?=\d)", "-\u2060", text)


def og_path(url: str) -> str:
    return f"/og/{url.strip('/') or 'index'}.png"


def og_cards() -> dict[str, Card]:
    """Page address -> its card, in the page's language. A page with none shows its home's."""

    def card(url: str, title: str, note: str = "") -> tuple[str, Card]:
        return url, Card(title, note)

    rs = [card(home_url(x), STRINGS[x]["descr"]) for x in LANGS]
    rs += [card(page_url("apps", x), STRINGS[x]["apps"]) for x in LANGS]
    rs += [card(x.url, x.title, str(x.date)) for x in get_posts().values()]
    rs += [card(x.url, x.title, x.tagline.replace("`", "")) for x in get_apps().values()]
    rs += [card(x.url, x.title) for x in get_pages().values()]
    return dict(rs)


def og_url(url: str, lang: str) -> str:
    """The card of the page at `url`, in full. A page with none shows its home's."""
    return BASE_URL + og_path(url if url in og_cards() else home_url(lang))


def seal_tilt(slug: str) -> float:
    """A seal is stamped by hand: a few degrees either way, the same for a page every time."""
    crc = crc32(slug.encode())
    return (1 if crc & 256 else -1) * (15 + crc % 31) / 10


def page(
    template: str,
    lang: str,
    title: str,
    urls: dict[str, str],
    descr: str | None = None,
    og_title: str | None = None,
    full_title: str | None = None,
    **ctx,
) -> str:
    """`urls` is this page in every language it exists in. `og_title` is for a shared link, where
    the title alone wouldn't say what the page is. `full_title` is the window's, in place of the
    title and the site's name."""
    sha = os.environ.get("COMMIT_SHA", "dev")
    many = len(urls) > 1
    url = urls.get(lang, "")
    alternates = urls | ({"x-default": urls["en"]} if "en" in urls else {})

    return render_template(
        template,
        lang=lang,
        t=STRINGS[lang],
        title=full_title or f"{title} :: {SITE}",
        og_title=og_title or title,
        og_image=og_url(url, lang),
        locale=LOCALES[lang],
        other_locales=[LOCALES[x] for x in urls if x != lang],
        site=SITE,
        descr=descr or STRINGS[lang]["descr"],
        home=home_url(lang),
        apps_url=page_url("apps", lang),
        about_url=page_url("about", lang),
        tags_url=page_url("tags", lang),
        atom_url=home_url(lang) + "atom.xml",
        rss_url=home_url(lang) + "rss.xml",
        canonical=BASE_URL + url if url else None,
        alternates=[(k, BASE_URL + v) for k, v in alternates.items()] if many else [],
        switch=[(k, None if k == lang else v) for k, v in urls.items()] if many else [],
        today=date.today(),
        sha=sha,
        sha_url=f"https://github.com/{REPO}/" + ("tree/main" if sha == "dev" else f"commit/{sha}"),
        work=WORK,
        **ctx,
    )


def index_page(lang: str) -> str:
    urls = {x: home_url(x) for x in LANGS}
    posts = list_posts(listed_posts(), lang)
    og_title = f"{SITE}: {STRINGS[lang]['descr']}"
    site = {
        "@type": "WebSite",
        "name": SITE,
        "url": BASE_URL + home_url(lang),
        "inLanguage": lang,
        "description": STRINGS[lang]["descr"],
        "author": {"@id": AUTHOR["@id"]},
    }

    return page(
        "index.html",
        lang,
        STRINGS[lang]["posts"],
        urls,
        og_title=og_title,
        full_title=og_title,
        section="blog",
        posts=posts,
        schema={"@context": "https://schema.org", "@graph": [site, AUTHOR]},
    )


def post_page(slug: str, lang: str) -> str:
    posts = get_posts()
    post = posts.get((slug, lang))
    if post is None:
        abort(404)

    sections = []
    html = render(post, site_urls(), sections)
    descr = describe(post)
    url = BASE_URL + post.url
    schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post.title,
        "description": descr,
        "datePublished": atom_date(post.date),
        "dateModified": atom_date(post.modified),
        "image": og_url(post.url, lang),
        "inLanguage": lang,
        "mainEntityOfPage": url,
        "url": url,
        "keywords": post.tags,
        "author": AUTHOR,
    }

    return page(
        "post.html",
        lang,
        post.title,
        {x: page_url(slug, x) for x in LANGS if (slug, x) in posts},
        descr=descr,
        schema=schema,
        post=post,
        html=html,
        toc=toc(sections),
        tilt=seal_tilt(slug),
        noindex=slug in unlisted_slugs(),
        tag_urls={x: tag_url(x, lang) for x in list_tags(listed_posts(), lang)},
        raw_url=f"https://raw.githubusercontent.com/{REPO}/main/{post.path}",
        edit_url=f"https://github.com/{REPO}/edit/main/{post.path}",
    )


def apps_page(lang: str) -> str:
    apps = [x for x in get_apps().values() if x.lang == lang]
    return page(
        "apps.html",
        lang,
        STRINGS[lang]["apps"],
        {x: page_url("apps", x) for x in LANGS},
        descr=", ".join(x.title for x in apps),
        section="apps",
        apps=apps,
    )


def app_page(slug: str, lang: str) -> str:
    apps = get_apps()
    x = apps.get((f"apps/{slug}", lang))
    if x is None:
        abort(404)

    unlisted = unlisted_slugs()

    return page(
        "app.html",
        lang,
        x.title,
        {k: page_url(x.slug, k) for k in LANGS if (x.slug, k) in apps},
        descr=x.blurb.replace("`", ""),
        section="apps",
        app=x,
        html=render(x, site_urls()),
        tilt=seal_tilt(x.slug),
        posts=[p for p in app_posts(x, get_posts()) if p.slug not in unlisted],
    )


def about_page(lang: str) -> str:
    pages = get_pages()
    x = pages["about", lang]
    html = render(x, site_urls())
    return page(
        "page.html",
        lang,
        x.title,
        {k: page_url("about", k) for k in LANGS if ("about", k) in pages},
        descr=describe(x),
        section="about",
        doc=x,
        html=html,
        tilt=seal_tilt(x.slug),
    )


def plural(n: int, lang: str, key: str) -> str:
    """`n` with its word from STRINGS: one, a few, many. Russian picks by the last digits: 1, 21 one;
    2-4, 22-24 a few; 11-14 and the rest many. English has only 1 and the rest."""
    if lang == "ru":
        i = 2 if n % 100 in range(11, 15) else 0 if n % 10 == 1 else 1 if n % 10 in (2, 3, 4) else 2
    else:
        i = 0 if n == 1 else 2

    return f"{n} {STRINGS[lang][key][i]}"


def tag_ink(count: int) -> int:
    """The ink a tag of this many posts takes in the cloud: 1 the darkest, 4 the palest."""
    return 4 if count < 2 else 3 if count < 3 else 2 if count < 5 else 1


def tags_page(lang: str) -> str:
    tags = list_tags(listed_posts(), lang)  # by name
    top = sorted(tags, key=lambda x: -len(tags[x]))  # stable: a tie stays by name

    return page(
        "tags.html",
        lang,
        STRINGS[lang]["tags"],
        {x: page_url("tags", x) for x in LANGS},
        descr=", ".join(top),
        section="tags",
        tags=[
            (x, tag_url(x, lang), plural(len(posts), lang, "post_forms"), tag_ink(len(posts)))
            for x, posts in tags.items()
        ],
    )


def tag_page(tag: str, lang: str) -> str:
    tags = {x: list_tags(listed_posts(), x) for x in LANGS}
    if tag not in tags[lang]:
        abort(404)

    return page(
        "tag.html",
        lang,
        STRINGS[lang]["tagged"].format(tag),
        {x: tag_url(tag, x) for x in LANGS if tag in tags[x]},
        descr=STRINGS[lang]["tagged"].format(tag),
        section="tags",
        tag=tag,
        posts=tags[lang][tag],
    )


def feed(kind: str, lang: str) -> Response:
    """Only what is written in this language, so a reader of one gets no second copy of a post."""
    posts = [x for x in list_posts(public_posts(), lang) if x.lang == lang]
    urls = site_urls()
    xml = render_template(
        f"{kind}.xml",
        lang=lang,
        site=SITE,
        descr=STRINGS[lang]["descr"],
        home=BASE_URL + home_url(lang),
        self_url=f"{BASE_URL}{home_url(lang)}{kind}.xml",
        updated=max(x.modified for x in posts),
        entries=[
            (x, BASE_URL + x.url, absolute_html(render(x, urls), BASE_URL + x.url)) for x in posts
        ],
    )

    return Response(xml, mimetype=FEEDS[kind])


def sitemap_urls() -> dict[str, date | None]:
    """Every public page, with a date where the page has one."""
    posts = public_posts()
    docs = [*get_apps().values(), *get_pages().values()]
    rs = {home_url(x): None for x in LANGS}
    rs |= {x.url: None for x in docs}

    for lang in LANGS:
        rs |= {page_url(x, lang): None for x in ("apps", "tags")}
        rs |= {tag_url(x, lang): None for x in list_tags(posts, lang)}

    rs |= {x.url: x.modified for x in posts.values()}
    return dict(sorted(rs.items()))


def not_found_page(lang: str) -> str:
    return page("404.html", lang, "404", {})


# static/'s files sit at the root. A catch-all route would lose to /<slug>/, which redirects to add the
# slash, so they go first, ahead of routing. The disk is asked each time: new files need no restart.
# safe_join drops a trailing slash, and /<slug>/ is never a file.
@app.before_request
def static_file():
    name = request.path.removeprefix("/")
    if any(private(x) for x in name.split("/")):
        abort(404)

    path = safe_join(str(STATIC_DIR), name)
    if path and os.path.isfile(path) and not request.path.endswith("/"):
        return send_file(path)


@app.get("/")
def index_en():
    return index_page("en")


@app.get("/ru/")
def index_ru():
    return index_page("ru")


@app.get("/404.html")
def not_found_en():
    return not_found_page("en")


@app.get("/ru/404.html")
def not_found_ru():
    return not_found_page("ru")


@app.get("/apps/")
def apps_en():
    return apps_page("en")


@app.get("/ru/apps/")
def apps_ru():
    return apps_page("ru")


@app.get("/apps/<slug>/")
def app_en(slug: str):
    return app_page(slug, "en")


@app.get("/ru/apps/<slug>/")
def app_ru(slug: str):
    return app_page(slug, "ru")


@app.get("/apps/<slug>/<file>")
def app_file(slug: str, file: str):
    if private(file) or not any(x == f"apps/{slug}" for x, _ in get_apps()):
        abort(404)

    return send_from_directory(APPS_DIR / slug, file)


@app.get("/about/")
def about_en():
    return about_page("en")


@app.get("/ru/about/")
def about_ru():
    return about_page("ru")


@app.get("/tags/")
def tags_en():
    return tags_page("en")


@app.get("/ru/tags/")
def tags_ru():
    return tags_page("ru")


@app.get("/tags/<tag>/")
def tag_en(tag: str):
    return tag_page(tag, "en")


@app.get("/ru/tags/<tag>/")
def tag_ru(tag: str):
    return tag_page(tag, "ru")


@app.get("/atom.xml")
def atom_en():
    return feed("atom", "en")


@app.get("/ru/atom.xml")
def atom_ru():
    return feed("atom", "ru")


@app.get("/rss.xml")
def rss_en():
    return feed("rss", "en")


@app.get("/ru/rss.xml")
def rss_ru():
    return feed("rss", "ru")


@app.get("/og/<path:name>.png")
def og_image(name: str):
    cards = {og_path(k): v for k, v in og_cards().items()}
    if request.path not in cards:
        abort(404)

    return Response(draw_card(cards[request.path]), mimetype="image/png")


@app.get("/sitemap.xml")
def sitemap():
    xml = render_template("sitemap.xml", base=BASE_URL, urls=sitemap_urls())
    return Response(xml, mimetype="application/xml")


# What an editor leaves beside a file while saving it, and Python's cache: none of it is an edit
SCRATCH = (".", "#", "__pycache__")


def stamps() -> dict[str, str]:
    """A hash of every file's path and time in pages/ and posts/, in the CSS, and in the rest of
    src/ and static/, so a rename or a deletion counts as much as an edit. Python files are left
    out: they restart the server, and the new one answers with a new `boot`."""
    rs = {"content": [], "styles": [], "code": []}
    todo = [(PAGES_DIR, "content"), (POSTS_DIR, "content"), (SRC, "code"), (STATIC_DIR, "code")]

    while todo:
        folder, kind = todo.pop()
        with suppress(FileNotFoundError), os.scandir(folder) as it:
            for x in it:
                if x.name.startswith(SCRATCH) or x.name.endswith("~"):
                    continue

                if x.is_dir():
                    todo.append((x.path, kind))
                    continue

                if kind == "code" and x.name.endswith(".py"):
                    continue

                # an editor's temporary file can be gone by now
                key = "styles" if kind == "code" and x.name.endswith(".css") else kind
                with suppress(FileNotFoundError):
                    rs[key].append(f"{x.path} {x.stat().st_mtime_ns}")

    return {k: hashlib.sha1("\n".join(sorted(v)).encode()).hexdigest()[:12] for k, v in rs.items()}


# The dev server's live update, asked for by live.js about once a second. Only with --debug, so the
# build never has it: a link to it would fail there. `boot` is new each time the reloader starts
# the app, so a page reloads only once the new server answers.
if app.debug:
    BOOT = os.urandom(4).hex()

    @app.get("/_live")
    def live():
        return stamps() | {"boot": BOOT}


def redirects() -> dict[str, str]:
    """REDIRECTS, and a renamed post's old addresses: its pages, its files and its cards."""
    posts = get_posts().values()
    pages = [(page_url(old, x.lang), x.url) for x in posts for old in x.aliases]
    files = [
        (f"/{old}/{f.name}", f"/{x.slug}/{f.name}")
        for x in posts
        for old in x.aliases
        for f in sorted(x.folder.iterdir())
        if f.is_file() and not private(f.name)
    ]
    cards = [(og_path(old), og_path(new)) for old, new in pages]
    return REDIRECTS | dict(pages + files + cards)


# after static_file(), ahead of routing, as a post's address would take an old slug
@app.before_request
def moved():
    new = redirects().get(request.path)
    if new:
        return redirect(new, 301)


@app.get("/<slug>/")
def post_en(slug: str):
    return post_page(slug, "en")


@app.get("/ru/<slug>/")
def post_ru(slug: str):
    return post_page(slug, "ru")


@app.get("/<slug>/<file>")
def post_file(slug: str, file: str):
    post = next((x for (k, _), x in get_posts().items() if k == slug), None)
    if private(file) or post is None:
        abort(404)

    return send_from_directory(post.folder, file)


@app.errorhandler(404)
def on_not_found(e):
    lang = "ru" if request.path.startswith("/ru/") else "en"
    return not_found_page(lang), 404
