(() => {
  const debugParam = "debug";
  const debugKey = "debug-menu-enabled";
  const gridKey = "debug-menu-grid-enabled";
  const themeKey = "debug-menu-theme";
  const root = document.documentElement;
  const url = new URL(window.location.href);
  const requestedDebug = url.searchParams.get(debugParam);

  const hasStorage = () => {
    try {
      localStorage.setItem("__debug_menu_test__", "1");
      localStorage.removeItem("__debug_menu_test__");
      return true;
    } catch {
      return false;
    }
  };

  const storageAvailable = hasStorage();

  const getStored = (key) => (storageAvailable ? localStorage.getItem(key) : null);
  const setStored = (key, value) => {
    if (storageAvailable) localStorage.setItem(key, value);
  };
  const removeStored = (key) => {
    if (storageAvailable) localStorage.removeItem(key);
  };

  const clearDebugParam = () => {
    if (!url.searchParams.has(debugParam)) return;

    const nextUrl = new URL(window.location.href);
    nextUrl.searchParams.delete(debugParam);
    window.history.replaceState(window.history.state, "", nextUrl);
  };

  const setTheme = (theme) => {
    if (theme === "light" || theme === "dark") {
      root.dataset.theme = theme;
      setStored(themeKey, theme);
      return;
    }

    root.removeAttribute("data-theme");
    removeStored(themeKey);
  };

  const resetTheme = () => {
    root.removeAttribute("data-theme");
  };

  const isGridEnabled = () => getStored(gridKey) !== "0";

  const setGridEnabled = (enabled) => {
    setStored(gridKey, enabled ? "1" : "0");
  };

  const applyGrid = (enabled) => {
    document.body?.classList.toggle("rhythm-grid-hidden", !enabled);
  };

  const exitDebugMode = () => {
    removeStored(debugKey);
    resetTheme();
    root.classList.remove("rhythm-grid-enabled");
    document.body?.classList.remove("rhythm-grid-enabled", "rhythm-grid-hidden");
    document.querySelector(".debug-menu")?.remove();
  };

  if (requestedDebug === "1") {
    setStored(debugKey, "1");
  } else if (requestedDebug === "0") {
    exitDebugMode();
  }

  clearDebugParam();

  const isDebugEnabled = () => getStored(debugKey) === "1";

  if (isDebugEnabled()) {
    setTheme(getStored(themeKey));
  }

  const installStyles = () => {
    if (document.getElementById("debug-menu-styles")) return;

    const style = document.createElement("style");
    style.id = "debug-menu-styles";
    style.textContent = `
      body.rhythm-grid-enabled:not(.rhythm-grid-hidden) {
        background-image: repeating-linear-gradient(
          to bottom,
          rgb(0 119 204 / 0.28) 0,
          rgb(0 119 204 / 0.28) 1px,
          transparent 1px,
          transparent var(--line-height-body, 24px)
        );
      }

      .debug-menu {
        position: fixed;
        right: var(--space-4, 1rem);
        bottom: calc(var(--line-height-body, 24px) * 3);
        z-index: 10000;
        display: inline-flex;
        align-items: center;
        gap: var(--space-1, 0.25rem);
        height: calc(var(--line-height-body, 24px) + var(--space-1, 0.25rem));
        padding: var(--space-1, 0.25rem);
        border-radius: var(--space-1, 0.25rem);
        background-color: var(--bg-color, canvas);
        color: var(--text-color, canvastext);
        box-shadow: 0 var(--space-1, 0.25rem) var(--space-2, 0.5rem) rgb(0 0 0 / 0.22);
        font: inherit;
        font-size: var(--font-size-small, 0.875rem);
        line-height: var(--line-height-body, 24px);
      }

      .debug-menu button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: var(--line-height-body, 24px);
        height: var(--line-height-body, 24px);
        padding: 0;
        border: 0;
        border-radius: var(--space-1, 0.25rem);
        background-color: transparent;
        color: var(--text-color, canvastext);
        font: inherit;
        outline: none;
        cursor: pointer;
      }

      .debug-menu button:focus,
      .debug-menu button:focus-visible {
        outline: none;
      }

      .debug-menu button:hover {
        background-color: var(--code-bg-color, color-mix(in srgb, canvastext 8%, canvas));
        color: var(--link-hover-color, currentcolor);
      }

      .debug-menu button[aria-pressed="true"] {
        color: var(--link-color, currentcolor);
      }

      .debug-menu button[aria-pressed="false"],
      .debug-menu-close {
        opacity: 0.72;
      }

      .debug-menu-close:hover {
        opacity: 1;
      }
    `;

    document.head.appendChild(style);
  };

  const createButton = ({ className, label, text }) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.setAttribute("aria-label", label);
    button.title = label;
    button.textContent = text;
    return button;
  };

  const initDebugMenu = () => {
    if (!isDebugEnabled()) return;

    installStyles();

    root.classList.add("rhythm-grid-enabled");
    document.body.classList.add("rhythm-grid-enabled");
    applyGrid(isGridEnabled());

    const panel = document.createElement("div");
    panel.className = "debug-menu";

    const gridButton = createButton({
      className: "debug-menu-grid",
      label: "Toggle grid",
      text: "▦",
    });
    gridButton.setAttribute("aria-pressed", "false");

    const themeButton = createButton({
      className: "debug-menu-theme",
      label: "Theme: system",
      text: "◐",
    });
    themeButton.setAttribute("aria-pressed", "false");

    const closeButton = createButton({
      className: "debug-menu-close",
      label: "Exit debug mode",
      text: "×",
    });

    const renderGrid = () => {
      const enabled = isGridEnabled();
      gridButton.setAttribute("aria-pressed", String(enabled));
    };

    const renderTheme = () => {
      const theme = getStored(themeKey);
      const normalizedTheme = theme === "light" || theme === "dark" ? theme : "system";
      const labels = {
        system: ["Theme: system", "◐"],
        light: ["Theme: light", "☀"],
        dark: ["Theme: dark", "☾"],
      };

      themeButton.title = labels[normalizedTheme][0];
      themeButton.setAttribute("aria-label", labels[normalizedTheme][0]);
      themeButton.textContent = labels[normalizedTheme][1];
      themeButton.setAttribute("aria-pressed", String(normalizedTheme !== "system"));
    };

    gridButton.addEventListener("click", () => {
      const nextEnabled = !isGridEnabled();
      setGridEnabled(nextEnabled);
      applyGrid(nextEnabled);
      renderGrid();
      gridButton.blur();
    });

    themeButton.addEventListener("click", () => {
      const currentTheme = getStored(themeKey);
      const nextTheme =
        currentTheme === "light" ? "dark" : currentTheme === "dark" ? "system" : "light";
      setTheme(nextTheme);
      renderTheme();
      themeButton.blur();
    });

    closeButton.addEventListener("click", () => {
      closeButton.blur();
      exitDebugMode();
      clearDebugParam();
    });

    renderGrid();
    renderTheme();
    panel.append(gridButton, themeButton, closeButton);
    document.body.appendChild(panel);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDebugMenu);
  } else {
    initDebugMenu();
  }
})();
