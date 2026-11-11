"""Refreshes pages/projects.json: the stars of every repo the apps name. Standard library only."""

import json
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
APPS = ROOT / "pages" / "apps"
OUT = ROOT / "pages" / "projects.json"

# The frontmatter's `repos:` and its indented `label: url` lines. `links:` can hold repos too, like
# badgelib, and those aren't the app's.
REPOS = re.compile(r"^repos:\n((?:[ \t]+.*\n)+)", re.MULTILINE)
REPO = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)$", re.MULTILINE)


def app_repos(path: Path) -> list[str]:
    _, meta, _ = path.read_text(encoding="utf-8").split("---\n", 2)
    m = REPOS.search(meta)
    rs = REPO.findall(m[1]) if m else []
    if not rs:
        raise ValueError(f"{path.relative_to(ROOT)}: no GitHub URL under `repos:`")

    return rs


def fetch_stars(repo: str) -> int:
    req = Request(
        f"https://api.github.com/repos/{repo}",
        headers={"Accept": "application/vnd.github+json"},
    )

    with urlopen(req, timeout=30) as rep:
        return json.load(rep)["stargazers_count"]


def main() -> None:
    repos = sorted({x for path in APPS.glob("*/en.md") for x in app_repos(path)})

    # all of them or nothing: a half-written file would drop stars from the site
    try:
        rs = [{"name": x, "stars": fetch_stars(x)} for x in repos]
    except (URLError, KeyError, ValueError) as e:
        sys.exit(f"update-projects: {e}")

    rs.sort(key=lambda x: (-x["stars"], x["name"]))
    OUT.write_text(json.dumps(rs, indent=2) + "\n", encoding="utf-8")

    print(f"{len(rs)} repos written to {OUT.name}")


if __name__ == "__main__":
    main()
