---
title: unjar
order: 8
tagline: Your browser's cookies, ready for curl, yt-dlp and scripts.
blurb: Reads the cookies of a local browser profile and exports them as a cookies.txt file, JSON or a Cookie header. A CLI and a Rust library.
language: Rust
repos:
  GitHub: https://github.com/vladkens/unjar
links:
  API docs: https://docs.rs/unjar
  Releases: https://github.com/vladkens/unjar/releases/latest
---

unjar reads the cookies of a browser profile on your machine and exports them as a `cookies.txt` file, JSON or a `Cookie:` header. Log in once in your browser, then give that session to curl, yt-dlp or your own script, without copying cookies by hand or a browser extension.

It's for scripts that need a logged-in session, and it's the recommended way to add an X account to [twscrape](/apps/twscrape/). It works as a command-line tool or as a Rust library without the CLI's dependencies.

It knows Chrome, Chromium, Edge, Brave, Vivaldi, Opera, Arc, Helium, Firefox and Safari, and finds their profiles for you. Chrome, Edge, Helium, Firefox and Safari are verified end to end on macOS, the others are implemented but not yet tested. Current Chromium-based browsers on Windows aren't supported: they protect cookies with App-Bound Encryption, and unjar doesn't bypass it.

## Install

Download the binary for macOS (Apple Silicon) from the [latest release](https://github.com/vladkens/unjar/releases/latest) and put `unjar` into a folder on your `PATH`. Or build it with Rust:

```sh
cargo install unjar
```

```sh
unjar list
unjar x.com
unjar gitlab.com | curl -b - https://gitlab.com/api/v4/user
```
