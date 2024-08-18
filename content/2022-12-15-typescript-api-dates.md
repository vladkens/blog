---
title: Better date parsing for REST API with TypeScript
slug: rest-api-date-parsing
date: 2022-12-15
taxonomies:
  tags: ["typescript", "api", "react"]
---

A little trick in TypeScript to make it easier to work with date strings in the API. Let’s say we have a model like this on the client:

```ts
type User = {
  id: number;
  username: string;
  createdAt: Date;
};
```

And we transfer this data in textual protocol in JSON format, e.g. via REST API or Websockets. And we get data in a format similar to this:

```text
GET /api/users/current
{
  "id": "1234567890",
  "username": "johndoe",
  "createdAt": "2020-01-01T00:00:00.000Z"
}
```

After that, you have to write data converters from the protocol model to the data model used in the application.

```ts
type UserDto = {
  id: number;
  username: string;
  createdAt: string;
}

const decodeUser = (dto: UserDto): User => {
  return {
    id: dto.id,
    username: dto.username,
    createdAt: new Date(dto.createdAt),
  };
}

const getCurrentUser = async (): Promise<User> => {
  const user = await get<UserDto>('/api/users/current');
  return decodeUser(user);
}

const u = await getCurrentUser()
console.log(typeof u.createdAt, u.createdAt instanceof Date) // string, false
```

Basically, if the API only has a few methods, it’s not a problem to write decoders from DTO models. But usually the API is much bigger. And why should we do it if we can do not? :)

In general, if we think about JSON format, it represents all basic types except date. So if we avoid the moment with string to date conversion, we won’t need any decodes at all. Let’s fix it.

```ts
import { parseISO } from "date-fns/esm";

const ISODateFormat = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d*)?(?:[-+]\d{2}:?\d{2}|Z)?$/;

const isIsoDateString = (value: unknown): value is string => {
  return typeof value === "string" && ISODateFormat.test(value);
};

const handleDates = (data: unknown) => {
  if (isIsoDateString(data)) return parseISO(data);
  if (data === null || data === undefined || typeof data !== "object") return data;

  for (const [key, val] of Object.entries(data)) {
    // @ts-expect-error this is a hack to make the type checker happy
    if (isIsoDateString(val)) data[key] = parseISO(val);
    else if (typeof val === "object") handleDates(val);
  }

  return data
};
```

And now we can update our http client to automatically turn date strings into a native date object.

```ts
const http = <T>(url: string, config?: RequestInit) => {
  return fetch(url, config).then((x) => handleDates(x.json()) as Promise<T>);
};

const get = <T>(url: string) => {
  return http<T>(url);
}

const getCurrentUser = (): Promise<User> => {
  return http<User>("/api/users/current");
};

const u = await getCurrentUser()
console.log(typeof u.createdAt, u.createdAt instanceof Date) // object, true

// or if you use axios you can make it event better

axios.interceptors.response.use((rep) => {
  handleDates(rep.data);
  return rep;
});

const getCurrentUser = async (): Promise<User> => {
  const rep = await axios.get<User>("/api/users/current");
  return rep.data;
};
```