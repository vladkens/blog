---
title: TimeWiz
order: 10
tagline: Compare cities and find a time that works across timezones.
blurb: A visual timezone board. Put cities on one timeline, spot the overlap and pick a time window. No account, and it works offline as a PWA.
language: TypeScript
repos:
  GitHub: https://github.com/vladkens/timewiz
links:
  Website: https://timewiz.cc
---

<img class="logo" src="logo.svg" alt="TimeWiz logo" />

Most world clock tools answer one question: what time is it there? TimeWiz is built for the next one: when does this actually line up well? It's a visual board where you compare cities on one timeline, spot the overlap and pick a sensible time window.

It's for distributed teams and anyone planning calls, streams, releases or travel across timezones. There are 5500+ cities and timezones. You set a Home city, keep different setups in tabs, highlight a range on the timeline, then copy it, email it or export it to Google Calendar or `.ics`. You can share the current setup with a link.

It's a lighter alternative to [World Time Buddy](https://worldtimebuddy.com). I don't remember exactly why I made my own version.

## Use

Open [timewiz.cc](https://timewiz.cc). No account, no setup. To run it locally:

```sh
pnpm install
pnpm dev
```
