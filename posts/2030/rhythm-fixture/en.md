---
title: Rhythm Fixture
date: 2030-01-01
tags: ["test"]
draft: true
---

This is a temporary page for checking how article elements sit on the vertical rhythm grid. It includes the same kinds of content that appear across regular posts: headings, paragraphs, lists, quotes, code blocks, images, inline HTML, tables, horizontal rules, and reference lists.

This paragraph checks inline flow with [a regular link](/coding-agents-statusline/), `inline_code`, _emphasis_, **strong text**, and a longer sentence that wraps onto the next line without breaking the baseline grid.

## Headings

This paragraph follows an `h2`. It should start on the rhythm grid and leave a clean module before the next heading.

### H3 heading

This paragraph follows an `h3`. Real articles use this for subsections inside longer technical posts.

#### H4 heading

This paragraph follows an `h4`. It checks lower-level headings without adding extra decoration.

##### H5 heading

This paragraph follows an `h5`. It should remain readable and aligned with the same rhythm.

###### H6 heading

This paragraph follows an `h6`. It is mostly here to catch edge cases in heading sizing.

## A section heading long enough to wrap onto a second line, with `inline_code` in it and then some more words

Wrapped headings keep every line in a row of its own.

### A subsection heading that is also long enough to wrap onto a second line on any window, with _emphasis_

#### A fourth level heading long enough to wrap onto a second line on any window you are likely to read this in

##### A fifth level heading long enough to wrap onto a second line on any window you are likely to read this in

###### A sixth level heading long enough to wrap onto a second line on any window you are likely to read this in

Superscript<sup>1</sup> and subscript<sub>2</sub> stay inside their line, and so does a hard<br>line break.

## Lists

Unordered lists show up in feature summaries and pros/cons sections:

- First item with `inline_code` and a short sentence.
- Second item with [a link](https://example.com) and enough text to wrap onto a second line so the row height is visible.
- Third item with _emphasis_ and **strong text**.

Ordered lists show up in setup steps and reference notes:

1. Prepare the configuration file.
2. Run the command and inspect the output.
3. Update the article when the behavior changes.

Nested lists, and items with paragraphs and code:

- Outer item
  - Inner item with `inline_code`
  - Inner item long enough to wrap onto a second line so the nested row height is visible as well
    1. Third level
- Outer item with a paragraph

  A second paragraph in the same item, long enough to wrap onto a second line and show the row height.

  ```sh
  echo "code inside a list item"
  ```

- Last item

## Blockquotes

> Command-like notes and callouts are sometimes written as blockquotes. This one is intentionally long enough to wrap, so the left rule, padding, and line rhythm can be checked together.

The paragraph after a quote should return to the grid without an awkward jump.

> A quote with two paragraphs, a list and code:
>
> - An item in a quote
> - Another item with `inline_code`
>
> ```sh
> echo "code inside a quote"
> ```
>
> The last paragraph of the quote.

Text after the second quote.

## Code Blocks

Short shell snippets are common:

```sh
pnpm install
pnpm run dev
```

One line of code sits in a row of its own:

```sh
pnpm run dev
```

Four lines take three rows, five take four:

```sh
one
two
three
four
```

```sh
one
two
three
four
five
```

Code straight after a heading:

#### Code heading

```sh
pnpm install
```

A line of code wider than any column has to scroll inside its block, and the text after it stays on the grid:

```sh
echo "a very long line of code that runs past the column, past the field on the right and past any window you are likely to read this in, on and on"
```

Longer typed code should keep copy buttons, overflow, and line rhythm sane:

```ts
type Client = {
  name: string;
  status: "active" | "paused";
  configPath: string;
};

const clients: Client[] = [
  { name: "Codex", status: "active", configPath: "~/.codex/config.toml" },
  { name: "Claude Code", status: "paused", configPath: "~/.claude/settings.json" },
];
```

## Images

Markdown image:

![Codex statusline](/coding-agents-statusline/20260521-0.png)

Raw HTML image:

<img src="/og-image-generator/ogi-image-generator-1.png" alt="OG image generator preview" />

Inline SVG:

<svg viewBox="0 0 1200 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Inline SVG rhythm test"><rect x="0" y="0" width="1200" height="120" fill="#111"></rect><circle cx="72" cy="60" r="36" fill="#ffb600"></circle><text x="140" y="74" fill="#fff" font-size="42" font-family="Open Sans, Arial, sans-serif">Inline SVG block</text></svg>

Image linking out:

[![Codex statusline](/coding-agents-statusline/20260521-0.png)](https://example.com/out)

Raw image linking out:

<a href="https://example.com/out"><img src="/og-image-generator/ogi-image-generator-2.png" alt="OG image generator preview" /></a>

An image in a list, one alone in an item and one in the middle of text:

- ![aws console](/aws-ecs-cluster/aws-ecs-cluster-1.png)
- Text before ![terminal](/aws-python-lambda/aws-python-lambda-cli.png) and text after.

A very wide image:

![wide](/from-iterm-to-wezterm/20250109-2.png)

An animated image:

![macmon](/macmon/macmon-2.webp)

An SVG file, sized from its viewBox:

![seal](/seal.svg)

Raw SVG sized by width and height, with no viewBox:

<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Sized SVG"><rect width="600" height="200" fill="#777"></rect></svg>

An external image, pinned in the build:

<img src="https://raw.githubusercontent.com/vladkens/apigen-ts/HEAD/logo.svg" alt="logo" />

An image in a table:

| Picture                                                | Name |
| ------------------------------------------------------ | ---- |
| ![seal](/seal.svg)                                     | Seal |
| ![wide](/og-image-generator/ogi-image-generator-1.png) | Card |

Text after media should land back on the grid.

## Tables

| Client      | Statusline setup   | Config file               |
| ----------- | ------------------ | ------------------------- |
| Codex       | Interactive blocks | `~/.codex/config.toml`    |
| Claude Code | Command output     | `~/.claude/settings.json` |
| Starship    | Prompt modules     | `~/.config/starship.toml` |

The table should not break the rhythm around the paragraphs before and after it.

| Metric            | Current value | Notes                               |
| ----------------- | ------------: | ----------------------------------- |
| Font size         |          17px | Body text size                      |
| Line height       |          24px | Main vertical grid step             |
| Code size         |          15px | Inline code should not inflate rows |
| Max content width |         880px | Same page container                 |

Longer cells should wrap cleanly without turning the table into a visual mess.

| Area        | What to check                                                                                                                   | Result  |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------- | ------- |
| Wrapping    | A longer sentence inside a table cell should wrap without destroying the row spacing or pushing text into neighboring columns.  | Pending |
| Links       | [Example link](https://example.com) should look like a link but stay calm inside dense tabular content.                         | Pending |
| Inline code | Values like `status_line`, `/context`, and `browser_use` should stay readable and should not make the row taller for no reason. | Pending |

After the last table, this paragraph should land back on the same vertical rhythm.

## Horizontal Rule

This paragraph appears before a horizontal rule.

---

This paragraph appears after a horizontal rule and should keep the same vertical rhythm.

### Heading before a rule

---

## Heading after a rule

---

---

Two rules in a row, then text.

## References

Reference-style lists appear at the end of a few posts:

1. <https://example.com/reference-one>
2. <https://example.com/reference-two>
3. [Named reference link](https://example.com/reference-three)
