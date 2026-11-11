---
title: apigen-ts
order: 5
tagline: A typed TypeScript client from your OpenAPI spec, in one file.
blurb: Turns an OpenAPI or Swagger spec into a single typed `api-client.ts` on native fetch. Pure Node.js, supports OpenAPI 2.0, 3.0 and 3.1.
language: TypeScript
repos:
  GitHub: https://github.com/vladkens/apigen-ts
links:
  npm: https://npm.im/apigen-ts
posts:
  - simple-typescript-api-client-generator
---

<img class="logo" src="logo.svg" alt="apigen-ts logo" />

apigen-ts turns an OpenAPI spec into a typed TypeScript client with one command. The output is a single `api-client.ts` with no runtime dependencies. Every method returns the exact response type from your schema, so there's no casting and no `any`. It uses native `fetch`, which you can override for auth, retries or logging, and it can filter large schemas by path or tag.

It's most useful when the backend isn't JavaScript. With FastAPI and React, for example, you can't share contracts through code, and a generated client keeps both sides in sync.

The standard generator is written in Java and produces many files. I used swagger-typescript-api for a while, until its interfaces changed a few times and I had to fix several projects. I have a couple of NestJS and FastAPI projects in support mode that just need a simple, stable generator that won't change often, so I wrote my own.

## Install

```sh
pnpm add -D apigen-ts
```

Generate a client from a local file or a URL:

```sh
pnpm apigen-ts ./openapi.json ./api-client.ts
pnpm apigen-ts https://petstore3.swagger.io/api/v3/openapi.json ./api-client.ts
```

Then use it:

```ts
import { ApiClient } from "./api-client"

const api = new ApiClient({
  baseUrl: "https://example.com/api",
  headers: { Authorization: "secret-token" },
})

await api.pet.getPetById(1) // → Pet
```
