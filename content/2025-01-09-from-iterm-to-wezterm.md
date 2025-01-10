---
title: From iTerm To WezTerm
slug: from-iterm-to-wezterm
date: 2025-01-09
taxonomies:
  tags: ["tools", "terminal", "cli"]
extra:
  medium: https://medium.com/p/24db2ccb8dc1
  devto: https://dev.to/vladkens/from-iterm-to-wezterm-1meo
---

![WezTerm](/20250109-0.png)

For many years, I used [iTerm2](https://github.com/gnachman/iTerm2) as my main terminal emulator and probably spent hundreds of hours in it. Overall, I was satisfied with it, despite some strange recent updates like adding AI features, KeyChain integration, and [security vulnerabilities](https://news.ycombinator.com/item?id=42579472).

In recent years, new terminal emulators have appeared. I tried using them mainly for testing [macmon](https://github.com/vladkens/macmon). A couple of years ago, I tried switching to [kitty](https://github.com/kovidgoyal/kitty), which was faster due to GPU acceleration. However, it required too much customization and still looked very non-native for macOS. GPU acceleration was added to iTerm as well, so I stayed with it.

I also tried [Alacritty](https://github.com/alacritty/alacritty), but it is very basic and lacks the features I need. Recently, I tested [Ghostty](https://github.com/ghostty-org/ghostty), which has gained huge attention – it has nice defaults, but its RAM usage is concerning (around 250MB per empty tab). Currently, it also lacks [buffer search](https://github.com/ghostty-org/ghostty/issues/189), which makes the terminal useless for me.

I heard a lot of positive feedback about [WezTerm](https://github.com/wez/wezterm) from [bobuk](https://github.com/bobuk). So I decided to try it out and use it for some time – and I am very satisfied with it.

The next part of the article will be about how to make WezTerm understandable for iTerm users to try it or switch completely.

## Initial

WezTerm can be installed from Homebrew:

```sh
brew install --cask wezterm
```

When you first open WezTerm, it looks plain, non-native, and not very functional. But actually, it has everything you need. This is because WezTerm is cross-platform, unlike iTerm2, so the author left minimal default settings, leaving the rest of the configuration to the user. My goal is to achieve a similar experience in WezTerm as I had in iTerm.

![WezTerm on first launch](/20250109-1.png)

WezTerm does not have a graphical interface for configuration, and the setup is done through a Lua file (this is unusual for me, but Vim users are familiar with it). The configuration file can be located at `~/.wezterm.lua` or `~/.config/wezterm/wezterm.lua`. I prefer the second path because it is where [Fish](https://github.com/fish-shell/fish-shell) and [starship](https://github.com/starship/starship) store configs too.

Create a configuration file:

```sh
mkdir -p ~/.config/wezterm/ && touch ~/.config/wezterm/wezterm.lua
```

And then add the boilerplate code for configuration:

```lua
local wezterm = require "wezterm"
local config = wezterm.config_builder()
local action = wezterm.action

-- (here will be added actual configuration)

return config
```

## Appearance

First, I want to change the default font, its size, and disable ligatures (because it's important to see the actual characters in case of some logs).

```lua
config.font = wezterm.font {
  family = 'JetBrains Mono',
  weight = 'Medium',
  harfbuzz_features = { 'calt=0', 'clig=0', 'liga=0' }, -- disable ligatures
}
config.font_size = 14.0
config.line_height = 1.0
```

Save the file, and the changes should be applied immediately (yes, no reload required!).

Next, I want to change the theme and set it to follow the current system theme automatically. For the past year, I have been using [Catppuccin](https://github.com/catppuccin/catppuccin) themes, and I am very happy with them. They rarely have issues where some text colors blend with the background. To make the theme switch automatically based on the current system theme, we need to write a small Lua function (I copied it from the documentation):

```lua
local function scheme_for_appearance(appearance)
  if appearance:find "Dark" then
    return "Catppuccin Macchiato"
  else
    return "Catppuccin Latte"
  end
end

config.color_scheme = scheme_for_appearance(wezterm.gui.get_appearance())
```

I forgot to mention that the Catppuccin theme, like many other popular themes, is pre-installed in WezTerm, so you don't need to install it separately like in iTerm, which is very cool. Of course, you can also set up [your own colors](https://wezfurlong.org/wezterm/config/appearance.html#defining-your-own-colors).

The default padding also seems a bit large, so let's make it smaller. I also had a Blinking Line Cursor (I don't remember if this is the default or not in iTerm). Let's set both configurations:

```lua
config.window_padding = { left = '0.5cell', right = '0.5cell', top = '0.5cell', bottom = '0.5cell' }
config.default_cursor_style = 'BlinkingBar'
```

## Window style

In iTerm, I used the Minimal theme to save vertical space for tabs. We can do the same in WezTerm (the default tabs don't look very good). Also possible to add some transparency and blur to the window. I didn't use this in iTerm, but let's try it now:

```lua
config.window_decorations = 'RESIZE|INTEGRATED_BUTTONS'
config.window_background_opacity = 0.96
config.macos_window_background_blur = 20
```

![WezTerm tabs decoration](/20250109-2.png)

## Maximize on start-up

In iTerm, I usually set large values for Cols/Rows to make the start window bigger. This approach is a bit outdated, so let's make the window open in full screen when the terminal starts.

```lua
-- https://github.com/wez/wezterm/issues/3299#issuecomment-2145712082
wezterm.on("gui-startup", function(cmd)
  local active = wezterm.gui.screens().active
	local tab, pane, window = wezterm.mux.spawn_window(cmd or {})
  window:gui_window():set_position(active.x, active.y)
  window:gui_window():set_inner_size(active.width, active.height)
end)
```

## Key bindings

Finally, the most important part is setting up hotkeys – it's hard to give up what you've been used to for years. An important thing for me is Split Panels with `Cmd + D` / `Cmd + Shift + D`. `Cmd + W` should close the current active panel, not the whole tab. `Cmd + K` – clear the current screen. `Cmd + ←` / `Cmd + →` for start/end of the line. I think these are all defaults from iTerm, so let's make them the same in WezTerm:

```lua
config.keys = {
  { key = 'd', mods = 'CMD|SHIFT', action = action.SplitVertical { domain = 'CurrentPaneDomain' } },
  { key = 'd', mods = 'CMD', action = action.SplitHorizontal { domain = 'CurrentPaneDomain' } },
  { key = 'k', mods = 'CMD', action = action.ClearScrollback 'ScrollbackAndViewport' },
  { key = 'w', mods = 'CMD', action = action.CloseCurrentPane { confirm = false } },
  { key = 'w', mods = 'CMD|SHIFT', action = action.CloseCurrentTab { confirm = false } },
  { key = 'LeftArrow', mods = 'CMD', action = action.SendKey { key = 'Home' } },
  { key = 'RightArrow', mods = 'CMD', action = action.SendKey { key = 'End' } },
  { key = 'p', mods = 'CMD|SHIFT', action = action.ActivateCommandPalette },
}
```

WezTerm also has a Command Execution menu. I haven't used it much yet, but just in case, I bind it to the same keys as in VSCode / Zed – `Cmd + Shift + P`.

_Note: In the configuration, the `key` value is case-sensitive, so `{ key = 'd', ... }` and `{ key = 'D', ... }` are different things (basically `key='D'` is the same as `key='d', mods='SHIFT'`). I initially got confused with this._

## Fin

Overall, I am very satisfied with WezTerm and have fully switched to using it daily. One cool feature I want to mention is the quick connect to servers in Known hosts via SSH (Command Palette → type server name → Enter OR Nav Bar → Shell → Click on server name). WezTerm also has [Workspaces](https://wezfurlong.org/wezterm/recipes/workspaces.html) – an alternative to tmux, but I haven't used it actively yet.

Here a [gist](https://gist.github.com/vladkens/f2ae7c374c1752c4b1581c5e7dffa900) with the final config from this article.

---

1. <https://wezfurlong.org/wezterm/config/files.html>
2. <https://alexplescan.com/posts/2024/08/10/wezterm/>
