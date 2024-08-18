---
title: Keep Type Guards valid after refactoring in TypeScript
slug: typescript-guards
date: 2022-12-03
taxonomies:
  tags: ["typescript", "tricks"]
---

TypeScript is a great language for writing applications with type safety checks. Extending or refactoring code in TypeScript is much easier than in plain JavaScript.

TypeScript has a nice built-in functionality for interface narrowing — Type Guards. But they don’t always protect against errors during code extension / refactoring, especially if you have a large project.

## Problem description

For example, we have a tea store. We sell two kinds of tea: loose and bagged. We show all the goods in one list. Each type of product has humanised link, and in the name of the product we want to specify the number of grams or the number of tea bags in a pack.

```tsx
import React from "react";

type Tea = { id: number; name: string; price: number };

type LooseTea = Tea & { weight: number };
type BaggedTea = Tea & { size: number };

const isLooseTea = (x: Tea): x is LooseTea => "weight" in x;
const isBaggedTea = (x: Tea): x is BaggedTea => "size" in x;

const getLink = (x: Tea): string => {
  if (isLooseTea(x)) return `/loose-tea/${x.id}`;
  if (isBaggedTea(x)) return `/bagged-tea/${x.id}`;
  throw new Error("Unknown tea");
};

const getTitle = (x: Tea): string => {
  if (isLooseTea(x)) return `${x.name} / ${x.weight}g`;
  if (isBaggedTea(x)) return `${x.name} / ${x.size} teabags`;
  throw new Error("Unknown tea");
};

const TeaItems: React.FC<{ items: Tea[] }> = ({ items }) => {
  return (
    <ul>
      {items.map((x) => (
        <li key={x.id}>
          <a href={getLink(x)}>{getTitle(x)}</a>
        </li>
      ))}
    </ul>
  );
};
```

Later, we got large tea bags (for the teapot) and changed our data model:

```tsx
type BaggedTea = Tea & { bags: number; weightPerBag: number };
```

After that we get an error in `getTitle` function and fix it:

```tsx
// before:
const getTitle = (x: Tea): string => {
  if (isLooseTea(x)) return `${x.name} / ${x.weight}g`;
  // Property 'size' does not exist on type 'BaggedTea'. ts(2339)
  if (isBaggedTea(x)) return `${x.name} / ${x.size} teabags`;
  throw new Error("Unknown tea");
};

// after:
const getTitle = (x: Tea): string => {
  if (isLooseTea(x)) return `${x.name} / ${x.weight}g`;
  if (isBaggedTea(x)) return `${x.name} / ${x.bags} teabags ~ ${x.weightPerBag}`;
  throw new Error("Unknown tea");
};
```

Everything seems to be fine and TypeScript doesn’t found any error. But in fact during the rendering process an "Unknown tea" error will occur, because the Type Guard in the `getLink` function is no longer pass in `isBaggedTea` guard.

## Problem solution

The problem with our Type Guard is that internally we check for the presence of a field in the object. This is a JavaScript operation and it is not typed in any way.

Well, let’s handle that. I propose to use a factory function to create Type Guard functions based on the data-model fields.

```tsx
type AnyObject = Record<string, any>;

// https://stackoverflow.com/a/52991061
type RequiredKeys<T> = {
  [K in keyof T]-?: AnyObject extends Pick<T, K> ? never : K
}[keyof T];

const createShapeGuard = <T extends AnyObject>(...keys: RequiredKeys<T>[]) => {
  return (obj: unknown): obj is T => {
    if (typeof obj !== "object" || obj === null) return false;

    for (const key of (keys as string[])) {
      if (!(key in obj)) return false;
    }

    return true;
  };
};
```

Now let’s rewrite our Type Guards in a new way:

```tsx
const isLooseTea = createShapeGuard<LooseTea>("weight")
const isBaggedTea = createShapeGuard<BaggedTea>("bags", "weightPerBag")
```

Everything works fine now. If we change the data structure again in the future, TypeScript will check and tell us that there is now an error in our Type Guard:

```tsx
type BaggedTea = Tea & { bags: number; bagWeight: number };

// Argument of type '"weightPerBag"' is not assignable to parameter of type 'RequiredKeys<BaggedTea>'.ts(2345)
const isBaggedTea = createShapeGuard<BaggedTea>("bags", "weightPerBag")
```

---

That’s all for now. If this information was helpful to you, don’t forget to subscribe to receive notifications of new posts.
