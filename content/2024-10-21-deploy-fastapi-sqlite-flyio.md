---
title: Deploy FastAPI application with SQLite on Fly.io
slug: deploy-fastapi-with-sqlite-on-flyio
date: 2024-10-21
taxonomies:
  tags: ["docker", "python", "sqlite", "devops"]
extra:
  medium: https://medium.com/p/5ed1185fece1
  devto: https://dev.to/vladkens/deploy-fastapi-application-with-sqlite-on-flyio-3da1
---

![post cover image](/sqlite-flyio.png)

Cloud solutions are good for medium and large projects, but too heavy for small personal projects. If you want to launch something small (a few api endpoins and a small repository), there are three options:

- Use the same approaches as for "big" projects (AWS ECS/EKS, RDS), but they are redundant, and infrastructure code can be larger than code of the actual project. Also it's expensive (~$100).
- Use serverless solutions (Lambda, Vercel). Most cloud providers have such solutions, but these services have difficulties with simple databases – they provide cheap vendor solutions (AWS) or require a managed database, which again is expensive (mostly nothing for serverless, ~$20 for DB)
- Use VPS with Docker. It is cheap (~$5 for small machine) and almost no need to manage infrastructure, but deployments sucks (needs private or self-hosted regestry, SSH access from CI).

I usually write my small applications using SQLite, it's a handy little single file database that works in any programming language and can be copied to local machine to analyze data for example. So I was looking for some middleware solution that combines the serveless approach, ease of deployment and ability to use SQLite and found Fly.io.

## Setup

If you don't have an account in Fly.io – you need to [create](https://fly.io/app/sign-up) it. Also [CLI tool](https://fly.io/docs/flyctl/install/) called `flyctl` required to manage projects. Fly.io can be deployed both locally and from CI.

`flyctl` makes deploy from project's root folder from Dockerfile, which is cool, because same Dockerfile can be used in other systems. For play with Fly.io, I prepared a simple FastAPI project that stores state in database – generic url shortener with click counting.

`Dockerfile`:

```Dockerfile
FROM python:3.13-alpine
WORKDIR /app

COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . /app

ENV HOST=0.0.0.0 PORT=8080
EXPOSE ${PORT}
CMD uvicorn main:app --host ${HOST} --port ${PORT}
```

`main.py`:

```py
import asyncio
import random
import string
from urllib.parse import urlparse

import aiosqlite
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

DB_PATH = "/data/app.db"

app = FastAPI()

async def get_db() -> aiosqlite.Connection:
    if db := getattr(get_db, "_db", None):
        if db.is_alive:
            return db

    db = await aiosqlite.connect(DB_PATH, loop=asyncio.get_event_loop())
    db.row_factory = aiosqlite.Row

    qs = """
    CREATE TABLE IF NOT EXISTS links (
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        short_code TEXT PRIMARY KEY,
        full_url TEXT NOT NULL,
        clicks INTEGER DEFAULT 0
    )
    """

    await db.execute(qs)
    await db.commit()

    setattr(get_db, "_db", db)
    return db

def random_code(length=8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for x in range(length))

def is_valid_url(url: str) -> bool:
    try:
        parts = urlparse(url)
        return all([parts.scheme, parts.netloc])
    except ValueError:
        return False

@app.post("/")
async def shorten(url: str, req: Request):
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")

    host = req.headers.get("host")
    if host is None:
        raise HTTPException(status_code=500, detail="Missing host header")

    short_code = random_code()
    db = await get_db()
    qs = "INSERT INTO links (short_code, full_url) VALUES (?, ?)"
    await db.execute(qs, (short_code, url))
    await db.commit()

    return f"https://{host}/{short_code}"

@app.get("/")
async def list_links():
    db = await get_db()
    qs = "SELECT short_code, full_url, clicks FROM links ORDER BY created_at DESC"
    async with db.execute(qs) as cursor:
        return await cursor.fetchall()

@app.get("/{short_code}")
async def redirect(short_code: str):
    db = await get_db()
    qs = """
    UPDATE links SET clicks = clicks + 1 WHERE short_code = ?
    RETURNING full_url
    """

    async with db.execute(qs, (short_code,)) as cursor:
        if row := await cursor.fetchone():
            return RedirectResponse(row["full_url"])

    raise HTTPException(status_code=404)
```

`requirements.txt`:

```
aiosqlite
fastapi
uvicorn
```

## Deploy

To deploy our code, first we need to create a Fly.io project. This can be done either in the web interface or with `flyctl`. To create proejct with CLU tool in root folder (where code located) flyctl launch should be runned. This command will offer to select desired hardware and will create `fly.toml` file:

```sh
fly launch --build-only
```

You can modify project in future by changing parameters in this file or via web ui. The basic `fly.toml` looks fine, but SQLite requires Storage, which can be created with:

```sh
fly volumes create sqlite_data -s 1 -r ams
```

where `-s 1` sets volume size to 1 GB (default is 3 GB), and `-r` is region in which volume will be created (use same region in which Fly.io project is created). You can always change storage size later.

The last thing to do is to add a `mounts` section to `fly.toml`, which attaches the volume to the application:

```toml
[mounts]
source = "sqlite_data"
destination = "/data"
```

`sqlite_data` is the name of the storage, `/data` is the path where volume will be connected. This is essentially same as `docker run --mount source=sqlite_data,target=/data` or corresponding Docker Compose section.

SQLite cannot be writable from more than one app, and Fly.io by default creates 2 instances for an app, so we can specify the number of replicas as one just in case:

```sh
fly scale count 1
```

All configurations are done now and we can deploy our app with command:

```sh
fly deploy
```

The app should boot successfully and the public DNS name will be printed to console. Now we can check it out by posting some url to shortener:

```sh
❯ curl -X POST 'https://fly-fastapi-sqlite.fly.dev/?url=https://example.com'
https://fly-fastapi-sqlite.fly.dev/8ydmfAcK
```

Then we can visit this link, it should redirect to `https://example.com`. Finally, we can check that clicks are updated:

```sh
❯ curl -s 'https://fly-fastapi-sqlite.fly.dev/' | jq
[
  {
    "short_code": "8ydmfAcK",
    "full_url": "https://example.com",
    "clicks": 1
  }
]
```

To check that database state saved between deployments, we can perform new deployment with `fly deploy` and check that links list remained same as above (1 link, 1 click).

## Migrations

If you are using an external solution for migrations, rather than running them from code when app starts, then only way to run migration is to put it in Dockerfile as part of the RUN command.

## Backup

We can connect to machine with `fly ssh console` and then in `/data` folder interact with database file. Also we can copy database file to local machine with:

```sh
fly ssh sftp get /data/app.db ./app-backup.db
```

## Conclusion

Fly.io is a simple and convenient service for deploying applications. Deploy works from Docker Containers, additional services include PSQL, Redis, S3 like storage (unlike Vercel). It's cheap, the cheapest service costs 3 dollars (1 shared CPU / 256 MB) – maybe even less, if you have little traffic – container shuts down after a few minutes without activity and automatically turns on when traffic appears.

On downside, there is no built-in solution for scheduled tasks – instead, the official solution is to set up a separate server with `crontab` and run tasks from it – it's kind of creepy.

---

1. <https://fly.io/docs/rails/advanced-guides/sqlite3/>
2. <https://matthewsetter.com/deploy-go-sqlite-app-flydotapp/>
3. <https://programmingmylife.com/2023-11-06-using-sqlite-for-a-django-application-on-flyio.html>
