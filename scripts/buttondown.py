"""Makes the newsletter's email for a post's English version: a draft in Buttondown, or the same
draft again with its text replaced. The email is short, the post's card, its description and a link
to the site, so it reads the same in any mail client and the post itself is read on the site. The
owner checks the draft and sends it by hand: the API key has no right to send.

The API key is BUTTONDOWN_API_KEY, from the Keychain by kc.

  kc run -- uv run python scripts/buttondown.py <slug>   # create the draft, or update it
  uv run python scripts/buttondown.py <slug> --dry       # print the email, send nothing
"""

import argparse
import os
import sys
from pathlib import Path

from curl_cffi import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from content import Post, describe, page_url, read_posts

SITE = "https://vladkens.me"
API = "https://api.buttondown.com/v1"
EDITOR = "https://buttondown.com/emails"
# what goes under every email, in Markdown as a post; no file, no footer
FOOTER = ROOT / "assets" / "mirrors" / "buttondown.md"


def card(post: Post) -> str:
    """The post's OG card, as app.og_path names it."""
    return f"{SITE}/og/{post.url.strip('/')}.png"


def compose(post: Post) -> dict:
    url = SITE + post.url
    body = [
        f"[![{post.title}]({card(post)})]({url})",
        describe(post),
        f"[Read it on vladkens.me →]({url})",
    ]
    if FOOTER.exists():
        body.append(FOOTER.read_text().strip())

    return {
        "subject": post.title,
        # Markdown, said outright: without the comment a newsletter set to the rich editor takes it as
        # HTML and shows the brackets
        "body": "<!-- buttondown-editor-mode: plaintext -->\n" + "\n\n".join(body) + "\n",
        "description": describe(post),
        "image": card(post),
        "canonical_url": url,
        "slug": post.slug,
    }


class Buttondown:
    def __init__(self, key: str):
        headers = {"authorization": f"Token {key}"}
        self.http = requests.Session(impersonate="chrome", timeout=60, headers=headers)

    def call(self, method: str, path: str, body: dict | None = None):
        rep = self.http.request(method, API + path, json=body)
        if rep.status_code >= 400:
            raise RuntimeError(f"{method} {path}: HTTP {rep.status_code}, {rep.text[:300]}")

        return rep.json()

    def emails(self) -> list[dict]:
        rs, url = [], "/emails"
        while url:
            page = self.call("GET", url)
            rs += page["results"]
            url = page["next"] and page["next"].removeprefix(API)

        return rs

    def find(self, post: Post) -> dict | None:
        """The email already made for the post, by its canonical address, the one it had before a
        rename too."""
        urls = {SITE + post.url} | {SITE + page_url(x, post.lang) for x in post.aliases}
        return next((x for x in self.emails() if x["canonical_url"] in urls), None)


def push(post: Post, bd: Buttondown) -> str:
    rep = requests.head(card(post), impersonate="chrome", timeout=30, allow_redirects=True)
    if rep.status_code != 200:
        raise RuntimeError(f"no card on the site yet, deploy it first: {card(post)}")

    email = compose(post)
    old = bd.find(post)
    if old and old["status"] != "draft":
        raise RuntimeError(f"{EDITOR}/{old['id']} is {old['status']}: an email goes out once")

    if old:
        rs = bd.call("PATCH", f"/emails/{old['id']}", email)
    else:
        # without a status Buttondown sends it at once
        rs = bd.call("POST", "/emails", email | {"status": "draft"})

    return f"{EDITOR}/{rs['id']}"


def main() -> None:
    cli = argparse.ArgumentParser(description="Make a post's newsletter email, as a draft.")
    cli.add_argument("slug")
    cli.add_argument("--dry", action="store_true", help="print the email, send nothing")
    args = cli.parse_args()

    post = read_posts(drafts=True).get((args.slug, "en"))
    if not post:
        sys.exit(f"buttondown: no post {args.slug} in English")

    if args.dry:
        email = compose(post)
        print(f"Subject: {email['subject']}\n\n{email['body']}", end="")
        return

    key = os.environ.get("BUTTONDOWN_API_KEY")
    if not key:
        sys.exit(
            "buttondown: no BUTTONDOWN_API_KEY: run it as "
            "`kc run -- uv run python scripts/buttondown.py ...`"
        )

    print(push(post, Buttondown(key)))


if __name__ == "__main__":
    main()
