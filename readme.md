# vladkens.me

Personal tech blog. I write about things I actually build and use — Rust, TypeScript, DevOps, macOS tooling, and occasionally something deeper when a topic deserves it.

Live at **[vladkens.me](https://vladkens.me)** · also cross-posted to [Medium](https://medium.com/@vladkens) and [dev.to](https://dev.to/vladkens)

## Stack

- [Flask](https://flask.palletsprojects.com/) — routes and dev server, frozen to static files by `src/freeze.py`
- [Jinja](https://jinja.palletsprojects.com/) — templating
- [markdown-it-py](https://github.com/executablebooks/markdown-it-py) and [Pygments](https://pygments.org/) — Markdown and code highlighting
- [Pillow](https://python-pillow.github.io/) — reads post image sizes and draws Open Graph images at build time
- [giscus](https://giscus.app/) — comments
- [Umami](https://umami.is/) — analytics
- [oxfmt](https://oxc.rs/docs/guide/usage/formatter.html) — formatting: `brew install oxfmt` here, `npx` in CI
- Cloudflare Pages — hosting, deployed with `npx wrangler`

## Cross-post tools

- [markdown-to-medium](https://github.com/rnag/markdown-to-medium) / [web](https://ritviknag.com/markdown-to-medium/)
