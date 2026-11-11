---
title: url-normalize
order: 9
tagline: Превращает любую строку, похожую на URL, в чистый https://-адрес или null.
blurb: Небольшая TypeScript-библиотека, которая приводит грязные URL и голые домены к одному каноничному виду и вместо исключений возвращает null.
language: TypeScript
repos:
  GitHub: https://github.com/vladkens/url-normalize
links:
  npm: https://npm.im/url-normalize
---

url-normalize превращает любую строку, похожую на URL, в чистый каноничный `https://`-адрес, а если не получается, возвращает `null`. По умолчанию ставит HTTPS, убирает `www`, сортирует query-параметры и отбрасывает стандартные порты. Понимает голые домены, protocol-relative URL и конвертирует Unicode в Punycode и обратно. Весит 980 байт в brotli, у него одна зависимость, есть сборки CJS и ESM.

Пригодится в коде на JavaScript и TypeScript, который получает URL от людей или со страниц и должен их сравнивать, хранить или показывать. На невалидный ввод приходит `null`, так что try/catch не нужен. `extractDomain` и `humanizeUrl` идут в комплекте.

Есть ещё [normalize-url](https://github.com/sindresorhus/normalize-url). Отличия — экспорт и CJS, и ESM, `null` вместо исключения и встроенные утилиты для доменов и отображения.

## Установка

```sh
npm i url-normalize
```

```ts
import { urlNormalize } from "url-normalize"

urlNormalize("example.com")
// → "https://example.com"

urlNormalize("//www.example.com:443/../foo/bar?b=2&a=1#tag")
// → "https://example.com/foo/bar?a=1&b=2"

urlNormalize("example") // → null
```
