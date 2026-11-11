---
title: url-normalize
order: 9
tagline: Turn any URL-like string into a clean https:// URL, or null.
blurb: A small TypeScript library that turns messy URLs and bare domains into one canonical form, and returns null instead of throwing.
language: TypeScript
repos:
  GitHub: https://github.com/vladkens/url-normalize
links:
  npm: https://npm.im/url-normalize
---

url-normalize turns any URL-like string into a clean, canonical `https://` URL, and returns `null` if it can't. By default it uses HTTPS, removes `www`, sorts query params and strips default ports. It handles bare domains, protocol-relative URLs and Unicode to Punycode in both directions. It's 980 bytes with brotli, has one dependency and ships CJS and ESM.

It's for JavaScript and TypeScript code that takes URLs from people or scraped pages and needs to compare, store or show them. Invalid input gives `null`, so there's no try/catch. `extractDomain` and `humanizeUrl` come with the package.

There's also [normalize-url](https://github.com/sindresorhus/normalize-url). The differences are dual CJS and ESM exports, `null` instead of throwing, and the built-in domain and display utilities.

## Install

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
