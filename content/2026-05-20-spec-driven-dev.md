---
title: Spec-Driven Development in Practice
slug: spec-driven-dev
date: 2026-05-20
taxonomies:
  tags: ["tools", "ai"]
---

Tried two tools for Spec-Driven Development on my pet project — [delta-farmer](https://github.com/vladkens/delta-farmer) (51 files, 12k lines of code). Compared `spec-kit` and `cc-thingz`: ran each through two cases — security analysis and regular coding.

## Tools

**spec-kit** ([github](https://github.com/github/spec-kit)) — open source toolkit for Spec-Driven Development. Helps you focus on product scenarios and predictable results instead of vibe coding from scratch. Works on top of different coding agents, generates separate files for each step.

**cc-thingz** ([github](https://github.com/umputun/cc-thingz)) — a set of skills for Claude Code, installed via plugins / marketplace api. Basically a ready-made workflow inside Claude, not a separate wrapper around different agents.

### Setup, workflow and artifacts

`spec-kit` is designed as a more universal thing for different agents, but you pay for that with a separate CLI wrapper, its own templates and its own file structure. The flow is a sequence of separate commands: `/speckit-specify` -> `/speckit-plan` -> `/speckit-tasks` -> `/speckit-implement`, plus `/speckit-clarify` for spec refinement. One task creates multiple files.

A separate problem with `spec-kit` is the `.specify` folder. This is its internal structure where it stores some data and workflow metadata. It's not clear what to add to git and what not to. I didn't find any clear recommendations or best practices for team work in the documentation.

`spec-kit` also inserts a link to the current task directly into `CLAUDE.md` / `AGENTS.md`. Any new Claude session immediately sees it and works in the context of that task — you can't just have a regular conversation about the project or plan something else in parallel.

`cc-thingz` is simpler in this sense: it's tied directly to Claude Code and installed in its ecosystem as a set of skills. The pipeline is also fixed: `/brainstorm` -> `/plan:make` -> `/plan:review` -> `/plan:exec`, but it feels simpler. One task gets one file.

### Planning

In `spec-kit`, planning is split into several separate commands. First you run `/speckit-specify <task-description>`: the tool analyzes the task, looks at the source code, sometimes asks clarifying questions — you answer in chat by literally sending the letter `A` / `B` / `C` or typing your own answer (no interactive mode like in plan-mode).

After that `spec-kit` writes files to disk, and then you manually review them. You open the files, read them, check if the agent described the task correctly. If something is wrong, you write about it in chat — the tool generates an updated version.

Next step — `/speckit-plan`. The agent tries to write a technical spec based on the earlier description. Same process: generate, review, comment — until the result is good enough.

The last planning command is `/speckit-tasks`. It breaks the main task into subtasks. Same format. Basically the whole flow in `spec-kit` works the same way at each step: a command runs, the tool writes files to disk, and you have to validate them manually.

Inside `specs/<task-name>/` you end up with files like `spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `checklists/requirements.md`, and more. Each next step adds new files or updates old ones, so one task quickly grows into a lot of text that needs to be read and validated by hand.

There's also `/speckit-clarify` — to brainstorm a solution before writing the technical spec and before breaking it down.

`cc-thingz` works differently. It starts with `/brainstorm`: after you describe the task, the tool asks questions in interactive mode. You can pick a ready answer or type your own — it's not just chat, it's more like a menu with options (like plan-mode).

After `/brainstorm` the agent immediately suggests next steps: continue planning, review yourself, send to auto-review, or save. If you choose auto-review, other agents check the plan, find problems, and make fixes. So a big part of the review is built into the flow before you even look at it yourself.

Then you can either continue right in the same window, or save the file and come back later with `/plan:make <file>`. At this step the agent adds a technical plan and task list to the file. Everything goes into one Markdown file in `docs/tasks/`, and new info is just appended at the end.

After that the agent again offers options: run the plan through review again, save it, or start implementing. When the work is done, the file moves to `docs/tasks/completed`. Because everything lives in one file, it's easier to read diffs, easier to follow changes, and you don't have to think about which file to open.

### Executing tasks

In `spec-kit`, implementation starts with `/speckit-implement specs/<spec>`, and then the agent starts working on the task and writing code.

In `cc-thingz`, implementation starts with `/plan:exec`. You can run it with a file in a new session or continue right after planning. Then the agent goes through the subtasks one by one, writes code, adds tests as it goes, runs them to check the result, and at the end runs everything through an additional review by another agent.

## Task 1. Supply chain hardening

A Python trading automation project, distributed via `git clone + uv run`. Dependencies are described in `pyproject.toml` using `>=` ranges, `uv.lock` is not committed, so when cloning users get random versions from PyPI with no guarantees.

I needed to figure out how to protect such a project from supply chain issues, without external services like Renovate or Dependabot. Which files to commit, how to pin versions and how to update them later (using `pnpm` as a reference), how to be sure all deps are safe before release. Plus a reference to [best practices](https://github.com/lirantal/pypi-security-best-practices).

### Planning

First I gave both tools the same task description and ran the first pass. For `cc-thingz` it was `/brainstorm`, for `spec-kit` — `/speckit-specify`.

Then I ran the agent's proposed solution through a critic agent. `spec-kit` has `/speckit-clarify` for that, and `cc-thingz` after the first pass offered three options itself: commit the plan, review yourself, or send to another agent for review. I chose the last option.

`cc-thingz` produced a clear plan. The task came down to four changes: commit `uv.lock` — this gives reproducible installs and SHA256 verification; add `exclude-newer = "7 days"` — blocks packages published less than 7 days ago (protection against timing attacks like the LiteLLM case); enable `only-binary = [":all:"]` — prevents `setup.py` execution during install, wheels only; add `uv audit` for CVE scanning before releases. And separately — switch deploy to `uv sync --locked` for deterministic server installs.

`spec-kit` at the `/speckit-clarify` step started asking weird questions like "what to do if `uv audit` runs in an offline environment — skip the PR or not".

It also randomly suggested sending CVE notifications through the telegram integration in the code. That integration is used for trade start / stop — the bot saw a piece of code, didn't understand what it was for, and mixed up internal app logic with external security tooling.

Also, even though the project uses `uv`, it kept pulling pip-based solutions from the article instead of using proper uv tools. For example, it suggested `uv run pip-audit`, even though `uv` already has its own `uv audit`.

Then in planning mode it broke things into 21 subtasks — literally a separate item for every tiny thing.

### Implementation

The task itself is simple, so both were able to implement it from the plan without much trouble.

The `cc-thingz` result was clean and easy to read. `spec-kit` used some unclear packages, so the result didn't even run. I didn't check if what it did actually works — I didn't trust the result and didn't bother running it.

## Task 2. Real coding task

Task description (580 words, 5 kb): what to do, where to get the data, and how to verify the result. I intentionally didn't name specific files — left everything up to the developer, like in real life.

The short version: there are three data sources. The user's general trade history (1), the provider's trade history across all users (2), and the last few days of trades from the provider for the specific user (3). The task was to download sources 2 and 3, filter source 1 by them, cache that to disk, and plug it into the program's output instead of what's there now (which is basically just source 1).

### Planning

The product task was already described well, so brainstorming wasn't really needed here. But I gave the same file to both tools anyway and asked them to start planning the technical implementation.

`cc-thingz` asked a few good questions about implementation, then proposed a plan. Then it offered two options: review the plan myself or send it to another agent. I chose the second — got the file for review, made a few small fixes, and committed the plan. The result was one file: 10.6 Kb, 158 lines, 1479 words, 7 tasks. It also asked about things I missed in the task description — like how to store the cache on disk and what the data types look like. The bug in this task was exactly that: two sources represent the same data differently — in one place it's `1000`, in another `1000.0`, and they don't map directly.

`spec-kit` didn't ask any additional questions on its own. After three commands (`specify` / `plan` / `tasks`) there was already a bunch of files to read and check: 40.5 Kb, 737 lines, 4761 words, 13 tasks. It's heavy to read even once, not to mention that these files change during the review process.

### Implementation

`cc-thingz` ran not directly, but through `ralphex`: https://github.com/umputun/ralphex. Basically Claude / Codex in YOLO mode in Docker. My command was: `ralphex --serve docs/plans/20260515-onyx-fills-filtering.md`. It runs slow: a full pass takes an hour to an hour and a half.

`spec-kit` ran via `/speckit-implement 002` (where `002` is the task number) in a new session.

When `ralphex` was already on the last task, my five-hour limit ran out. I had no idea what task `spec-kit` was working on at that point, because it didn't update its files during execution. With `cc-thingz` it was easier: it created a commit after each change, so the full history was there.

Resuming work in both tools is different. In `spec-kit` it's a regular Claude session: when the limit resets, you can keep writing in the same window. Or you can close it and reopen with `--resume`. With `ralphex` it's different: you can call it again with the same task file, and it figures out where it stopped last time because it marks checkboxes in the todo list as it goes. So it continues from the last stopping point. Obviously without `ralphex` — `cc-thingz` also works as a regular Claude session.

### Result

Nothing to brag about here: both solutions didn't work out of the box, and both needed manual fixes.

`cc-thingz` had a problem where the agent didn't ask me about the full data structure during planning and didn't fetch a sample from the data source, even though I wrote that the data is public. As a result it interpreted the `Time` field as a timestamp instead of an ISO format string, so the data didn't parse. No other startup problems, but the numbers were wrong. After several dozen minutes of debugging in a separate Claude session (I don't know how to connect to `ralphex` logs, so I opened a new one) it turned out the bot called the API with wrong parameters. Because of that, part of the data couldn't be filtered correctly by source.

`spec-kit` had different errors at startup: it decided to calculate the report for 2025, even though I clearly said to start from January 1, 2026. It ended up downloading data for a very long time and hit the rate limit. Then there was a lock/unlock error when writing files. It decided to store data in a separate file for each date, even though I asked to save everything in one file and append to it when updating. After startup — same problem with wrong numbers: had to go to chat, enable debug logs, figure it out, and fix.

Both wrote tests. `cc-thingz` tests pass. `spec-kit` tests don't — it didn't run them and didn't check if the generated code was correct.

You can see the code, task files, and how changes are organized in the diffs: [spec-kit](https://github.com/vladkens/delta-farmer/compare/0fd999fa...1e62367e) (11 files, 1206 lines) and [cc-thingz](https://github.com/vladkens/delta-farmer/compare/5f92ecfa...9692d9f3) (9 files, 760 lines). `spec-kit` has more changes, but a big part is its own spec files, not code. `cc-thingz` worked more closely with the actual codebase.

## Wrap up

Before testing both tools, I ran the second task myself — just in a Claude dialog in edit mode, without any spec. I didn't have a proper task description at that point: I just didn't understand where to get the data and how it was structured. So the whole investigation happened in chat — debugging together with the agent, looking at what came from the API, figuring out the structure. That took about two or three hours.

Once the task was clear, I could write a proper description — and that's exactly what I gave to both tools.

**My final verdict:**

**`spec-kit`** — tool with a clear idea, but annoying to work with. Generates a lot of files that you have to read and review manually. Planning took about an hour, then the agent ran for another hour, then another hour fixing what didn't work. Wrote tests but didn't run them. Left more artifacts than code. Overkill for a simple task.

**`cc-thingz`** — easier to work with. One file, interactive mode, built-in review. Same time pattern: an hour for the spec, an hour for implementation, an hour for fixes. Wrote tests and ran them. There were errors, but the reason is clear — the agent didn't clarify the data structure upfront and didn't fetch a sample from the public API. The result is more trustworthy, though it wasn't perfect either.

The whole thing — testing both tools on two tasks and writing this post — took me two days.

Full diffs for both tasks: [spec-kit](https://github.com/vladkens/delta-farmer/compare/e61bc2c0...1e62367e), [cc-thingz](https://github.com/vladkens/delta-farmer/compare/e61bc2c0...9692d9f3).

## A few final thoughts

Working with agents in this mode is generally fine, but the cognitive load is pretty high. You need to describe the task clearly upfront, carefully read everything the agent wrote during planning, and make sure it covered all the important parts. If that's done well, the agent works pretty reliably after that. In theory you could use that time to write a spec for the next task — but for now it's more of an illusion than a real parallel workflow.

Fully delegating code writing to the agent doesn't seem like a great idea to me. First, you end up poorly understanding what was actually written. Second, the agent makes bad decisions on its own — without explicit direction from a human it often makes logical mistakes or goes in the wrong direction. At least in my case. Tasks in dialog mode get done faster: you understand what's happening with the code, you control how the solution goes — and the agent makes fewer mistakes.

`cc-thingz` with `ralphex` is worth trying for really simple tasks. You write the task to a file, run it — and it goes. For that scenario it looks like a genuinely useful thing. But the app needs to be well-tested and have a clear structure — otherwise the agent has nothing to rely on, and you get what I got.
