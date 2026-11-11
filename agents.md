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

## Boundaries

- Change a post's text only when asked; `posts/2030/rhythm-fixture/en.md` is the owner's test page for the grid.
- Add a dependency only with the owner's approval.
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
4. Keep the owner's voice: plain and concrete, without `я` and `I` except in rare cases. One sentence holds one thought, as long as that thought needs, with ordinary clauses; don't chop it into fragments, don't string several thoughts or lists of things through commas, and put a colon or a dash only where Russian punctuation calls for one, not to chop a thought into pieces. Asides and clarifications (an example, a definition) go in parentheses. Say it directly, without bookish turns («казалось бы», «взять тот же», «главный минус в том, что») and without joining clauses by a reflexive «а». Use only facts from the owner, the repo or checked sources; mark anything unverified with `TODO`.
5. When the owner approves the text, move it to `posts/<year>/<slug>/`, translate it, and keep the same `slug` in both languages.
6. To share it for proofreading, publish it with `unlisted: true`; removing the flag lists it at the same address.
