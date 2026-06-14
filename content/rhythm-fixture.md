---
title: Rhythm Fixture
slug: rhythm-fixture
date: 2030-01-01
draft: true
taxonomies:
  tags:
    - test
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

## Lists

Unordered lists show up in feature summaries and pros/cons sections:

- First item with `inline_code` and a short sentence.
- Second item with [a link](https://example.com) and enough text to wrap onto a second line so the row height is visible.
- Third item with _emphasis_ and **strong text**.

Ordered lists show up in setup steps and reference notes:

1. Prepare the configuration file.
2. Run the command and inspect the output.
3. Update the article when the behavior changes.

## Blockquotes

> Command-like notes and callouts are sometimes written as blockquotes. This one is intentionally long enough to wrap, so the left rule, padding, and line rhythm can be checked together.

The paragraph after a quote should return to the grid without an awkward jump.

## Code Blocks

Short shell snippets are common:

```sh
pnpm install
pnpm run dev
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

![Codex statusline](/20260521-0.png)

Raw HTML image:

<img src="/ogi-image-generator-1.png" alt="OG image generator preview" />

Inline SVG:

<svg viewBox="0 0 1200 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Inline SVG rhythm test"><rect x="0" y="0" width="1200" height="120" fill="#111"></rect><circle cx="72" cy="60" r="36" fill="#ffb600"></circle><text x="140" y="74" fill="#fff" font-size="42" font-family="Open Sans, Arial, sans-serif">Inline SVG block</text></svg>

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

## References

Reference-style lists appear at the end of a few posts:

1. <https://example.com/reference-one>
2. <https://example.com/reference-two>
3. [Named reference link](https://example.com/reference-three)
