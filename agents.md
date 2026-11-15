# agents.md

Personal blog vladkens.me: a Flask app frozen to static files for Cloudflare Pages.

## Where things live

- `src/app.py`: every URL of the site. `src/content.py`: reading posts, Markdown, images. `src/freeze.py`: the crawl into `public/`. `src/og.py`: OG cards.
- `posts/<year>/<slug>/en.md`, optional `ru.md`, images beside them; shrink a new PNG with `png-squash` (from the owner's dotfiles: pngquant, then oxipng) before committing it. The year comes from the post's `date` and isn't in its URL, so a slug is unique across years; the build stops on either mismatch. `posts/drafts/`: articles in progress, never built.
- A post's `unlisted: true` builds it at its address with `noindex` and lists it nowhere: home, tags, feeds, sitemap, app pages. `draft: true` is never built, and wins over it.
- To rename a post, rename its folder and add the old slug to `aliases` in each language: the build redirects its pages, files and OG cards.
- `pages/apps/<slug>/`, `pages/about/` have the same shape as a post, without the year; `pages/projects.json` holds the apps' stars.
- `src/templates/`. `static/`: the site's files, served at the root, one flat folder. Only what the crawl reaches gets published, plus the files named in `START` in `src/freeze.py`: a new file nothing links to goes there. `assets/`: what only the build reads, never served: the art's sources for `scripts/make-art.py` and `scripts/make-ink.py`, and the OG cards' font. `code/`: sources the posts link to on GitHub, so it stays where it is.
- `make dev`, `make test`, `make build`. `make prepare` and `make check` run `oxfmt`: `brew install oxfmt`, or `OXFMT="npx --yes oxfmt@0.76.0"` as CI does. The repo has no Node files.
- `uv run python scripts/medium.py <slug>` pushes the English post to Medium as a draft, and again updates that draft: it also sets the canonical link, and the owner only checks it, publishes it by hand and then sets `medium:` to its URL. The agent runs it, and before a new draft proposes up to five of Medium's own tags: `--find <word>...` lists the tags for many words about the post, with their followers, stories and followers per story; mix broad tags with many readers per story and exact ones whose readers want this topic, show the owner the choice with its numbers, and pass the agreed tags in `--tags`. Without `--tags` a new draft takes the post's tags, and an update keeps Medium's. It speaks the web editor's protocol through `curl_cffi` with the owner's Medium cookies from `unjar`, and draws SVGs to PNG with headless Helium; `--dry` shows what it would send. An update of a published story replaces its whole text, but Medium keeps it aside until the owner presses Save and publish in its editor.
- `kc run -- uv run python scripts/devto.py <slug>` does the same on dev.to by its API, with `DEVTO_API_KEY` from the Keychain: an unpublished article, found again by its canonical link, and a published one only with `--live`. Its pictures stay on the site, so the post is deployed first, except SVGs: dev.to shows them as empty boxes, so the script draws each to PNG and uploads it to dev.to with the owner's cookies from `unjar`. Tags work the same way, four at most; `--find` gives the rank among dev.to's top tags.
- `kc run -- uv run python scripts/buttondown.py <slug>` makes the newsletter's email for the English post as a Buttondown draft, and again updates that draft, found by its canonical link: the post's OG card, its description and a link to the site, nothing of its text. The key can't send, so the owner checks the draft and sends it by hand; an email already sent is never touched. `--dry` prints it.
- All three add `assets/mirrors/<site>.md`, if it exists, under the post as its footer. `kc run -- uv run python scripts/mirrors.py` shows each post's copies: published or draft, how much of their text is still the post's, a canonical link that isn't the post, a post `updated` after its copy went out, a Medium edit held till Save and publish, and copies of no post; `canonical --apply` points them all to the blog. `stats` prints their views, reads, reactions and comments, with the change since the run before, and appends them to `~/.local/share/vladkens.me/mirrors.jsonl`.

## Boundaries

- Before any answer or text about a post (a translation, a lead, an announcement, a copy on another site), read the post itself and this file first, and check the result against the voice in "Writing a post".
- Apply each of the owner's rules as written and only where it says: a rule for Russian doesn't reach English, and "avoid" doesn't mean "never". When a rule and your own judgment differ, follow the rule and name the doubt once; don't argue for breaking it.
- Change a post's text only when asked; `posts/2030/rhythm-fixture/en.md` is the owner's test page for the grid.
- Readers in Russia can't reach Cloudflare, so the site has a mirror on GitHub Pages, `blog.vladkens.me` (the `mirror` job in `deploy.yml`). Don't propose anything a reader's browser calls on Cloudflare (counters, likes, comments, forms): it fails for them; anything that runs in the browser must work from the mirror too.
- Add a dependency only with the owner's approval.
- Only new posts go to Medium and dev.to. The old posts' copies stay as they are: never repost, refresh or update them, and don't propose it; a lower match in `mirrors.py` for them is expected. Drafts left on those sites, the bio, a held Medium edit and old copies with no post here are the owner's business: don't bring them up. Tell the owner only what needs them to act, without a list of optional ideas.
- Use a new artwork only with its artist's permission and credit; never redraw or crop a work without the owner's approval.

## Layout

- Vertical layout comes from `line-height` and `font-size`; a block's total height is a whole number of rows, and the text after it lands back on a line.
- Compute anything that depends on content, such as image and code block heights, in Python at build time; CSS only picks the result.
- Keep CSS flat: `MARK` sections in order, each selector once. `scripts/check-rhythm.py` lists what is banned.
- Use system fonts only on the site.

## Writing a post

Work top down in `posts/drafts/<slug>.md`, in the language the owner starts in:

1. Collect the owner's topics and raw notes in the file as they come, unsorted and unedited.
2. Agree the headings with the owner before writing any prose.
3. Develop one section at a time: the owner throws in points, the agent expands them and asks about what's missing. In proofreading, change the paragraph the owner is on right away, without asking; never touch the text below it, which the owner hasn't read yet.
4. Keep the owner's voice in every text written for them: plain and concrete; in Russian, don't repeat `я` from sentence to sentence: drop a personal pronoun wherever the sentence reads the same without it, and keep it where it's needed. English keeps its ordinary pronouns. One sentence holds one thought, as long as that thought needs, with ordinary clauses; don't chop it into fragments, don't string several thoughts or lists of things through commas, and put a colon or a dash only where Russian punctuation calls for one, not to chop a thought into pieces. Asides and clarifications (an example, a definition) go in parentheses. Say it directly, without bookish turns («казалось бы», «взять тот же», «главный минус в том, что») and without joining clauses by a reflexive «а». Use only facts from the owner, the repo or checked sources; mark anything unverified with `TODO`.
5. When the owner approves the text, move it to `posts/<year>/<slug>/`, translate it, and keep the same `slug` in both languages.
6. To share it for proofreading, publish it with `unlisted: true`; removing the flag lists it at the same address.

## Publishing a post

- Before a post goes out anywhere, check that its screenshots and diagrams show the current app and the current text, not an older version.
- A lead written for a feed (Habr's `leadData`) is shown apart from the body: the body must not open by repeating it.
- After any copy goes out or is updated (Habr, Medium, dev.to), read it back from the site, not from what was sent: every link works and every picture renders.
