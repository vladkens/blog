---
title: apigen-ts
order: 5
tagline: Типизированный TypeScript-клиент из OpenAPI-спеки, одним файлом.
blurb: Превращает спеку OpenAPI или Swagger в один типизированный `api-client.ts` на нативном fetch. Чистый Node.js, поддерживает OpenAPI 2.0, 3.0 и 3.1.
language: TypeScript
repos:
  GitHub: https://github.com/vladkens/apigen-ts
links:
  npm: https://npm.im/apigen-ts
posts:
  - simple-typescript-api-client-generator
---

<img class="logo" src="logo.svg" alt="Логотип apigen-ts" />

apigen-ts одной командой превращает OpenAPI-спеку в типизированный TypeScript-клиент. На выходе один файл `api-client.ts` без runtime-зависимостей. Каждый метод возвращает точный тип ответа из схемы, поэтому не нужны ни приведения типов, ни `any`. Запросы идут через нативный `fetch`, который можно подменить для авторизации, ретраев или логирования, а большие схемы можно фильтровать по пути или тегу.

Больше всего он полезен, когда backend не на JavaScript. Например, с FastAPI и React контракты через общий код не расшаришь, а сгенерированный клиент держит обе стороны в синхроне.

Стандартный генератор написан на Java и создаёт кучу файлов. Какое-то время я использовал swagger-typescript-api, пока там несколько раз не поменяли интерфейсы и мне не пришлось чинить несколько проектов. У меня есть пара проектов на NestJS и FastAPI в режиме поддержки, которым нужен только простой и стабильный генератор без частых изменений, поэтому я написал свой.

## Установка

```sh
pnpm add -D apigen-ts
```

Клиент генерируется из локального файла или по URL:

```sh
pnpm apigen-ts ./openapi.json ./api-client.ts
pnpm apigen-ts https://petstore3.swagger.io/api/v3/openapi.json ./api-client.ts
```

Дальше просто используешь:

```ts
import { ApiClient } from "./api-client"

const api = new ApiClient({
  baseUrl: "https://example.com/api",
  headers: { Authorization: "secret-token" },
})

await api.pet.getPetById(1) // → Pet
```
