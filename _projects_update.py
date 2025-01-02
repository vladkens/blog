import json
import os
import re

import httpx
from dotenv import load_dotenv


def main():
    url = f"{os.getenv("GHS_API_URL")}/api/repos"
    rep = httpx.get(url, headers={"x-api-token": os.getenv("GHS_API_KEY") or ""})
    rep.raise_for_status()
    rep = rep.json()
    rep = {x["name"]: x for x in rep["items"]}

    with open("projects.json") as fp:
        projects = json.load(fp)

    for project in projects:
        project["stars"] = rep.get(project["name"], {"stars": 0})["stars"]

    with open("projects.json", "w") as fp:
        raw = json.dumps(projects, indent=2)
        raw = re.sub(r'\[\n\s+"', '["', raw)
        raw = re.sub(r'"\n\s+\]', '"]', raw)
        fp.write(raw + "\n")


if __name__ == "__main__":
    load_dotenv()
    main()
