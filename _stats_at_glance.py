import os
import time
from collections import defaultdict
from datetime import datetime, timedelta

import frontmatter
import httpx
from dotenv import load_dotenv

load_dotenv()

DEVTO_TOKEN = os.environ["DEVTO_API_KEY"]
MEDIUM_COOKIE = os.environ["MEDIUM_COOKIE"]
CLOUDFLARE_TOKEN = os.environ["CLOUDFLARE_TOKEN"]
UMAMI_TOKEN = os.environ["UMAMI_TOKEN"]
UNAMI_SITE = "2314c16c-b72f-4f6e-8f5e-ee3abe39383e"

SINCE, UNTIL = "2024-01-01", "2025-01-01"

projects = """
vladkens/twscrape
vladkens/macmon
vladkens/ecloop
vladkens/ghstats
vladkens/apigen-ts
vladkens/url-normalize
vladkens/ogp
vladkens/timewiz
vladkens/fractions-math
vladkens/array-utils-ts
vladkens/compose-updater
"""

projects = projects.strip().split("\n")
GITHUB_API_URL = "https://api.github.com"


def fromiso(date_str: str):
    return datetime.fromisoformat(date_str).replace(tzinfo=None)


def fetch_all_pages(url, params):
    items = []
    while url:
        # print(f">> {url}")
        rep = httpx.get(url, params=params)
        rep.raise_for_status()
        items.extend(rep.json())
        url = rep.links.get("next", {}).get("url")
        time.sleep(1)

    return items


def get_commits(repo: str):
    url = f"{GITHUB_API_URL}/repos/{repo}/commits"
    dat = {"since": SINCE, "until": UNTIL, "per_page": 100}
    items = fetch_all_pages(url, dat)
    return len(items)


def get_closed_issues(repo):
    url = f"{GITHUB_API_URL}/repos/{repo}/issues"
    dat = {"since": SINCE, "until": UNTIL, "per_page": 100}
    items = fetch_all_pages(url, dat)
    return len(items)


def get_releases(repo):
    url = f"{GITHUB_API_URL}/repos/{repo}/releases"
    dat = {"since": SINCE, "until": UNTIL, "per_page": 100}
    items = fetch_all_pages(url, dat)
    since = fromiso(SINCE)
    items = [x for x in items if fromiso(x["created_at"]) >= since]
    return len(items)


def print_ghstats():
    totals = defaultdict(int)
    for project in projects:
        commits = get_commits(project)
        issues = get_closed_issues(project)
        releases = get_releases(project)
        totals["commits"] += commits
        totals["issues"] += issues
        totals["releases"] += releases
        print(f"{project}: {commits} commits, {issues} issues, {releases} releases")

    print(
        f"Totals: {totals['commits']} commits, {totals['issues']} issues, {totals['releases']} releases"
    )


def load_frontmatter(file: str):
    with open(f"content/{file}") as fp:
        post = frontmatter.load(fp)
        links = post.get("extra", {})
        medium = links.get("medium", None)
        devto = links.get("devto", None)
        return post["slug"], medium, devto


def load_medium(url: str):
    post_id = url.split("/")[-1]
    url = "https://medium.com/_/graphql"
    dat = {
        "operationName": "StatsPostReferrersContainerQuery",
        "variables": {"postId": post_id},
        "query": "query StatsPostReferrersContainerQuery($postId: ID!) {\n  post(id: $postId) {\n    id\n    title\n    referrers {\n      ...StatsPostReferrersContainer_referrer\n      __typename\n    }\n    totalStats {\n      views\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment StatsPostReferrersContainer_referrer on Referrer {\n  totalCount\n  type\n  ...StatsPostReferrersExternalList_referrer\n  __typename\n}\n\nfragment StatsPostReferrersExternalList_referrer on Referrer {\n  totalCount\n  ...StatsPostReferrersExternalRow_referrer\n  __typename\n}\n\nfragment StatsPostReferrersExternalRow_referrer on Referrer {\n  totalCount\n  postId\n  type\n  sourceIdentifier\n  platform\n  internal {\n    postId\n    collectionId\n    profileId\n    type\n    __typename\n  }\n  search {\n    domain\n    keywords\n    __typename\n  }\n  site {\n    href\n    title\n    __typename\n  }\n  __typename\n}\n",
    }

    rep = httpx.post(url, json=dat, headers={"Cookie": MEDIUM_COOKIE})
    # print(rep.status_code, rep.text)
    rep.raise_for_status()
    return rep.json()["data"]["post"]["totalStats"]["views"]


def load_devto(url: str):
    rep = httpx.get(url)
    rep.raise_for_status()
    post_id = int(rep.text.split('data-article-id="')[1].split('"')[0])

    url = f"https://dev.to/api/analytics/historical?start=2019-04-01&article_id={post_id}"
    rep = httpx.get(url, headers={"api-key": DEVTO_TOKEN})
    rep.raise_for_status()
    # return rep.json()["page_views_count"]

    views, comments, reactions = 0, 0, 0
    for k, v in rep.json().items():
        views += v["page_views"]["total"]
        comments += v["comments"]["total"]
        reactions += v["reactions"]["like"]

    return {"views": views, "comments": comments, "reactions": reactions}


def load_cloudflare(url: str):
    pass


def load_umami():
    st = int(time.time() - 60 * 60 * 24 * 365) * 1000
    et = int(time.time()) * 1000
    url = f"https://api.umami.is/v1/websites/{UNAMI_SITE}/metrics"
    dat = {"startAt": st, "endAt": et, "type": "url"}
    rep = httpx.get(url, headers={"x-umami-api-key": UMAMI_TOKEN}, params=dat)
    # print(rep.status_code, rep.text)
    rep.raise_for_status()

    res = defaultdict(int)
    for x in rep.json():
        slug = x["x"].split("#")[0].rstrip("/")
        if slug == "" or slug.startswith("/tags/"):
            continue

        res[slug] += x["y"]

    return res


def get_blog_stats():
    files = [x for x in os.listdir("content") if x.startswith("2024-")]
    files = sorted(files)
    umami_views = load_umami()
    # print(umami_views)
    for file in files:
        url, medium, devto = load_frontmatter(file)

        site_views = umami_views.get(f"/{url}", 0)
        devto_views = load_devto(devto)["views"] if devto else 0
        medium_views = load_medium(medium) if medium else 0
        total_views = site_views + devto_views + medium_views
        print(f"{url}\t{total_views}\t{site_views}\t{medium_views}\t{devto_views}")


print_ghstats()
# get_blog_stats()
