---
title: Как следить за лимитами в Codex и Claude Code
slug: coding-agents-statusline
date: 2026-05-21
taxonomies:
  tags: ["tools", "ai"]
---

Продолжаю настраивать coding-агенты под себя. [В прошлый раз](/spec-driven-dev/) был про процесс работы с ними, теперь мелкая деталь — контроль лимитов через statusline.

Я пользуюсь двумя coding-агентами: Codex и Claude Code. Оба меня устраивают, и я спокойно переключаюсь между ними: иногда потому, что в одном заканчиваются лимиты, иногда потому, что просто веду разные задачи в разных клиентах. Основным у меня стал Claude Code — именно там раньше всего появились skills, MCP и прочая рабочая обвязка. За это время вокруг него накопилось много настроек, и далеко не всё я перенёс в Codex. Как это нормально автоматизировать, я тоже не понял. Если кто-то уже решал такую синхронизацию между Claude Code и Codex, напишите в комментариях — буду рад ссылке или совету.

После того как месяц-полтора назад ввели лимиты, стало неудобно постоянно проверять их руками через `/status`. С контекстом та же история: чтобы понять, сколько ещё осталось до автокомпакта, нужно отдельно дёргать `/context`. Само по себе это несложно, но делать это постоянно быстро надоедает. При этом хотелось заранее видеть, когда лимит или контекст уже близко, чтобы успеть что-то сохранить руками. После автокомпакта модель у меня часто тупеет и забывает важные факты. Поэтому я полез смотреть, как это вообще можно отслеживать, и выяснил, что у обоих клиентов есть statusline. По умолчанию он и там и там довольно минималистичный и показывает в основном только текущую модель.

В Codex statusline настраивается адекватно. Достаточно написать `/statusline` и в интерактивном UI выбрать, что показывать. Дальше эти настройки сохраняются в `~/.codex/config.toml`.

Я для себя выбрал такой формат:

![Codex statusline](/20260521-0.png)

```text
gpt-5.4 medium · ~/Code/blog · Context 73% left · 5h 93% · weekly 92% · 258K window · 1.2M used
```

В Codex нельзя задать полностью свой формат строки. Можно только выбрать набор готовых блоков и их порядок.

В конфиге это выглядит так:

```toml
[tui]
status_line = ["model-with-reasoning", "current-dir", "context-remaining", "five-hour-limit", "weekly-limit", "context-window-size", "used-tokens"]
theme = "catppuccin-macchiato"
```

То есть это можно либо накликать через UI, либо просто отредактировать файл руками.

---

Что касается `claude-code`, у него тоже есть команда `/statusline`. Но вместо интерактивного меню с набором блоков, как в Codex, здесь подошли иначе — по-агентски: робот пытается прочитать мои bash / zsh / fish-конфиги и на их основе сгенерировать statusline.

Очевидно, я не стал давать ему доступ к файлам, потому что не хочу отправлять свои конфиги в Anthropic. Да и не очень понимаю, зачем они им, если на GitHub и так полно [dotfiles-репозиториев](https://github.com/search?q=dotfiles&type=repositories).

В `~/.claude/settings.json` можно указать команду, которая запускается при каждом обновлении statusline. Выглядит это так:

```jsonc
{
  // ...
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh",
    "padding": 0,
  },
}
```

Здесь `command` — это просто скрипт, который Claude Code будет запускать при обновлении statusline. На GitHub можно найти много разных реализаций. Например, такие безумные решения: [sirmalloc/ccstatusline](https://github.com/sirmalloc/ccstatusline), [Owloops/claude-powerline](https://github.com/Owloops/claude-powerline), [Haleclipse/CCometixLine](https://github.com/Haleclipse/CCometixLine), [hagan/claudia-statusline](https://github.com/hagan/claudia-statusline), [felipeelias/claude-statusline](https://github.com/felipeelias/claude-statusline). Безумными я их называю потому, что в эпоху, когда очередной npm-пакет ломают чуть ли не каждый день, ставить дополнительный софт через npm ради настолько простой задачи кажется [странной идеей](https://en.wikipedia.org/wiki/Npm_left-pad_incident).

Но идею у них позаимствовать можно. Команда запускается при каждом обновлении статуса, в `stdin` приходит JSON, который можно распарсить и отобразить как угодно. Документация по доступным полям: [Claude Code statusline docs](https://code.claude.com/docs/en/statusline#available-data)

В общем, в statusline приходит примерно такой набор данных:

```jsonc
{
  // shortened example; see docs for the full schema
  "session_id": "<session-id>",
  "transcript_path": "/Users/<user>/.claude/projects/<project>/<session-id>.jsonl",
  "cwd": "/Users/user/Code/blog",
  "session_name": "<session-name>",
  "model": { "id": "claude-sonnet-4-6", "display_name": "Sonnet 4.6" },
  "workspace": { "current_dir": "/Users/user/Code/blog" },
  "version": "2.1.126",
  "output_style": { "name": "default" },
  "context_window": {
    "total_input_tokens": 433,
    "total_output_tokens": 492,
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 1,
      "output_tokens": 92,
      "cache_creation_input_tokens": 299,
      "cache_read_input_tokens": 14201,
    },
    "used_percentage": 7,
    "remaining_percentage": 93,
  },
  "exceeds_200k_tokens": false,
  "fast_mode": false,
  "effort": { "level": "high" },
  "thinking": { "enabled": true },
  "rate_limits": {
    "five_hour": { "used_percentage": 62, "resets_at": 1779296400 },
    "seven_day": { "used_percentage": 22, "resets_at": 1779750000 },
  },
}
```

Вообще для кастомизации терминала я использую [starship.rs](https://starship.rs/). У них даже есть интеграция с Claude Code: [Statusline for Claude Code](https://starship.rs/advanced-config/#statusline-for-claude-code). Но блоков для часовых лимитов там нет — после того как их добавили в Claude, starship так и не обновился. Issue на GitHub висит: [starship/starship#7441](https://github.com/starship/starship/issues/7441). Насколько я понял, автор репозитория куда-то пропал, и уже несколько месяцев в проекте почти ничего не происходит.

Так что я просто попросил Claude написать bash-скрипт, который выведет строку в том же формате, что в Codex. Вышло что-то такое:

```bash
#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
get() { jq -r "$1" <<<"$input"; }

fmt_tokens() {
  awk -v n="$1" 'BEGIN {
    if      (n >= 1000000) printf "%.1fM", n / 1000000
    else if (n >= 1000)    printf "%.0fK", n / 1000
    else                   printf "%d",    n
  }'
}

model="$(get '.model.display_name')"
dir="$(get '.workspace.current_dir')"
dir="${dir/#"$HOME"/\~}"

context_remaining="$(get '(.context_window.remaining_percentage // 100)')% left"
five_hour="$(get '100 - .rate_limits.five_hour.used_percentage')%"
weekly="$(get '100 - .rate_limits.seven_day.used_percentage')%"
window="$(fmt_tokens "$(get '.context_window.context_window_size')")"
used="$(fmt_tokens "$(get '.context_window.context_window_size * .context_window.used_percentage / 100')")"

printf '%s · %s · Context %s · 5h %s · weekly %s · %s window · %s used\n' \
  "$model" "$dir" "$context_remaining" "$five_hour" "$weekly" "$window" "$used"

```

В итоге оба клиента начинают выглядеть одинаково:

![Matching statuslines](/20260521-1.png)

Единственный косяк, который я заметил в Claude Code: при открытии терминала statusline не показывается сразу в новых сессиях. Появляется только после первого взаимодействия с чатом (можно вызвать вручную через Cmd+Shift).

На этом всё. На настройку statusline и написание заметки ушло около трёх часов.
