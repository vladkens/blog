import json
import re

import httpx

repos = [
    ("vladkens/twscrape", "Python library for scraping X"),
    ("vladkens/macmon", "MacOS CLI tool for performance monitoring"),
    ("vladkens/ghstats", "Self-hosted GitHub stats for your repos"),
    ("vladkens/apigen-ts", "Generate TypeScript API clients from OpenAPI"),
    ("vladkens/ecloop", "secp256k1 elliptic curve brute-forcing"),
    ("vladkens/ogp", "Open Graph image generator as a service"),
    ("vladkens/timewiz", "Time zone viewer & meeting planner"),
    ("vladkens/badges", "Nice badges for your projects"),
]


def main():
    items = []
    for repo, desc in repos:
        rep = httpx.get(f"https://api.github.com/repos/{repo}")
        rep.raise_for_status()
        dat = rep.json()
        items.append(
            {
                "name": repo,
                "descr": desc or dat["description"],
                "langs": [dat["language"]],
                "stars": dat["stargazers_count"],
            }
        )

    items = sorted(items, key=lambda x: x["stars"], reverse=True)
    with open("projects.json", "w") as fp:
        raw = json.dumps(items, indent=2)
        raw = re.sub(r'\[\n\s+"', '["', raw)
        raw = re.sub(r'"\n\s+\]', '"]', raw)
        fp.write(raw + "\n")


if __name__ == "__main__":
    main()
