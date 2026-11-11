---
title: badges.ws
order: 6
tagline: SVG-бейджи по URL, на готовом сервисе или у себя.
blurb: Бейджи для README и документации, которые собираются из URL. Свой текст и цвета или живые данные из npm, PyPI, GitHub и ещё 20+ платформ.
language: Rust
repos:
  GitHub: https://github.com/vladkens/badges
links:
  Сайт: https://badges.ws
  badgelib: https://github.com/vladkens/badgelib
---

<img class="logo" src="logo.svg" alt="Логотип badges.ws" />

badges.ws делает SVG-бейджи из URL. Пишешь в адресе подпись, значение и цвет, и бейдж готов. Или указываешь npm, PyPI, GitHub и ещё 20+ платформ, и получаешь бейдж с живыми данными. Можно выбрать стиль, скругление, логотип из Simple Icons и анимацию.

Он для всех, у кого есть проект и нужны бейджи в README или документации. Бейджи в README моих проектов сделаны на нём. Можно брать готовый сервис или поднять свой одной командой Docker. А если хочется рендерить бейджи прямо в своём Rust-приложении, без отдельного сервиса, рендеринг вынесен в библиотеку [badgelib](https://github.com/vladkens/badgelib).

Писал его на Rust в конце 2024 и начале 2025. Это выглядело как довольно простая задача, но вылилось в несколько месяцев работы и дебагинга разных API.

## Использование

```text
https://badges.ws/badge/{label}-{message}-{color}
```

```markdown
[<img src="https://badges.ws/badge/Version-1.0.0-red" />](https://your-project.link)
```

## Self-hosted

```sh
docker run -d -p 8080:8080 ghcr.io/vladkens/badges:main
```
