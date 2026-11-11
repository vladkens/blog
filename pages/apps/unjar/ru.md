---
title: unjar
order: 8
tagline: Cookies из твоего браузера, готовые для curl, yt-dlp и скриптов.
blurb: Читает cookies локального профиля браузера и экспортирует их в cookies.txt, JSON или заголовок Cookie. CLI и Rust-библиотека.
language: Rust
repos:
  GitHub: https://github.com/vladkens/unjar
links:
  API docs: https://docs.rs/unjar
  Релизы: https://github.com/vladkens/unjar/releases/latest
---

unjar читает cookies из профиля браузера на твоей машине и экспортирует их в файл `cookies.txt`, JSON или заголовок `Cookie:`. Логинишься один раз в браузере и отдаёшь эту сессию curl, yt-dlp или своему скрипту, без ручного копирования cookies и без расширений.

Он для скриптов, которым нужна залогиненная сессия, и это рекомендуемый способ добавить аккаунт X в [twscrape](/apps/twscrape/). Работает как консольная утилита или как Rust-библиотека без зависимостей CLI.

Умеет работать с Chrome, Chromium, Edge, Brave, Vivaldi, Opera, Arc, Helium, Firefox и Safari и сам находит их профили. Chrome, Edge, Helium, Firefox и Safari проверены от начала до конца на macOS, остальные реализованы, но ещё не протестированы. Современные браузеры на Chromium под Windows не поддерживаются: там cookies защищены App-Bound Encryption, и обходить её unjar не будет.

## Установка

Скачай бинарник для macOS (Apple Silicon) из [последнего релиза](https://github.com/vladkens/unjar/releases/latest) и положи `unjar` в папку из `PATH`. Или собери через Rust:

```sh
cargo install unjar
```

```sh
unjar list
unjar x.com
unjar gitlab.com | curl -b - https://gitlab.com/api/v4/user
```
