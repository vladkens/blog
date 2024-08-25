---
title: Better forms handling with react-use-form
slug: react-form-handling
date: 2023-04-04
taxonomies:
  tags: ["typescript", "react"]
---

React-use-form is a powerful library that simplifies form handling in React applications. Its intuitive API and robust feature set make it an excellent choice for developers.

One of its standout features is the ability to work with custom components while minimizing re-renders of the main component, which is undeniably cool. This is achieved through the use of the Controller component, although its syntax may not be the most convenient.

In this article, I’ll demonstrate how to create a generic wrapper that makes it easy to use your own components with the full power of Controller.

---

Imagine we have a cool input component:

```tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { FC, useId } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

type SuperInputProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
};

const SuperInput: FC<SuperInputProps> = (props) => {
  const { label, value, onChange, error } = props;
  const id = useId();

  return (
    <div>
      <label htmlFor={id}>{label}</label>
      <input id={id} value={value} onChange={(e) => onChange(e.target.value)} />
      {error && <span>{error}</span>}
    </div>
  );
};

const schema = z.object({
  firstName: z.string().min(1, { message: "Required" }),
  lastName: z.string().min(1, { message: "Required" }),
});

const SuperForm: FC = () => {
  const { control } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
  });

  return (
    <form>
      <Controller
        control={control}
        name="firstName"
        render={({ field: { onChange, value }, fieldState: { error } }) => (
          <SuperInput label="First name" value={value} onChange={onChange} error={error?.message} />
        )}
      />
      <Controller
        control={control}
        name="lastName"
        render={({ field: { onChange, value }, fieldState: { error } }) => (
          <SuperInput label="Last name" value={value} onChange={onChange} error={error?.message} />
        )}
      />
    </form>
  );
};
```

The part about the Controller looks verbose. If you have a lot of forms in your application, it’s tedious to write it every time. Let’s make it better!

---

To do this, we first need to write some TypeScript helpers to get a list of fields in dot notation for a particular data type.

```ts
import { Primitive } from "react-hook-form";

type NestedImpl<K extends string | number, V, T> = V extends T
  ? K
  : V extends Primitive | Array<infer V>
    ? never
    : `${K}.${NestedByType<V, T>}`;

export type NestedByType<O, T> = {
  [K in keyof O]-?: K extends string ? NestedImpl<K, O[K], T> : never;
}[keyof O];

// test code

type A = { abc: string; xyz: number; nested1: { abc: number; xyz: string } };
type B = A & { arr: number[] };
type a1 = NestedByType<A, number>; // "xyz" | "nested1.abc"
type a2 = NestedByType<A, string>; // "abc" | "nested1.xyz"
type a3 = NestedByType<A, boolean>; // never
type a4 = NestedByType<B, number[]>; // "arr"
type a5 = NestedByType<B, string>; // "abc" | "nested1.xyz"
```

Now we need to make a small utility to comfortably retrieve errors from the form state for specific fields.

```ts
const getCtrlError = (formState: { errors: Record<string, any> }, name: string) => {
  const tokens = name.split(".");

  let value = formState.errors;
  for (const token of tokens) {
    if (value[token]) value = value[token];
  }

  return value && value.message ? (value.message as string) : undefined;
};
```

Finally, we can make our Controlled wrapper for custom components.

```tsx
import { FC } from "react";
import { Control, Controller, FieldValues } from "react-hook-form";

const makeCtrl = <T extends Pick<T, "value" | "onChange"> & { error?: string }>(
  Component: FC<T>,
  options: { errorKey?: string } = {}
) => {
  // react-hook-form has FieldPathByValue but it slow, so we use NestedByType
  const Wrapped = <D extends FieldValues, P extends NestedByType<D, T["value"]>>(
    props: Omit<T, "value" | "onChange" | "error"> & { control: Control<D>; name: P }
  ) => {
    const { control, name, ...rest } = props;
    const errorKey = options.errorKey ? `${name}.${options.errorKey}` : name.toString();

    return (
      <Controller
        control={control}
        // @ts-expect-error because of comment above
        name={name}
        render={({ field: { value, onChange }, formState }) => {
          const error = getCtrlError(formState, errorKey.toString());
          const props = { ...rest, value, onChange, error } as unknown as T;
          return <Component {...props} />;
        }}
      />
    );
  };

  return Wrapped;
};
```

I assume that the component for which we do wrapper has properties: value, onChange, error. These properties will be removed from the resulting component and automatically inserted into child component. But if you want to “remove” other fields, you can add them to generic type of makeCtlr function, e.g.: `makeCtrl<SomeType, "field_to_remove_1" | "field_to_remove_2">(...)`.

---

And now it can be used somehow like this:

```tsx
const SuperInputCtrl = makeCtrl(SuperInput); // create new component

const SuperForm: FC = () => {
  const { control } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
  });

  return (
    <form>
      <SuperInputCtrl control={control} name="firstName" label="First name" />
      <SuperInputCtrl control={control} name="lastName" label="Last name" />
    </form>
  );
};
```

Now it looks much shorter, but still safe (the wrapper only allows fields that match the value type in the input). The validation error is automatically filled in. Only the input is re-rendered during data entry, not the entire form.
