---
title: badges.ws
order: 6
tagline: SVG badges from a URL, hosted or self-hosted.
blurb: Badges for READMEs and docs, built from a URL. Use your own text and colors, or live data from npm, PyPI, GitHub and 20+ other platforms.
language: Rust
repos:
  GitHub: https://github.com/vladkens/badges
links:
  Website: https://badges.ws
  badgelib: https://github.com/vladkens/badgelib
---

<img class="logo" src="logo.svg" alt="badges.ws logo" />

badges.ws makes SVG badges from a URL. Put a label, a message and a color in the address and you have a badge, or point it at npm, PyPI, GitHub and 20+ other platforms for one that shows live data. You can choose the style, radius, a logo from Simple Icons and an animation.

It's for anyone who maintains a project and wants badges in a README or docs. The badges in my own READMEs come from it. You can use the hosted version or run your own with one Docker command. If you'd rather render badges inside your own Rust app, without a service, the rendering part is a separate library, [badgelib](https://github.com/vladkens/badgelib).

I wrote it in Rust at the end of 2024 and the beginning of 2025. It looked like a fairly simple task, but turned into several months of work and debugging various APIs.

## Use

```text
https://badges.ws/badge/{label}-{message}-{color}
```

```markdown
[<img src="https://badges.ws/badge/Version-1.0.0-red" />](https://your-project.link)
```

## Self-host

```sh
docker run -d -p 8080:8080 ghcr.io/vladkens/badges:main
```
