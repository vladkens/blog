// The owner's menu over the page, a row of buttons in the window's bottom right corner: the row grid, a forced theme, the OG card,
// and close on the corner itself. ?debug=1 or five quick clicks in that corner open it, and it stays open from page to page until
// closed. Nothing of it shows on a page that hasn't asked.
(() => {
  const root = document.documentElement;
  const DARK = "(prefers-color-scheme: dark)";
  const PRESSES = 5;
  const PRESS_WINDOW = 2000;
  const OPEN_WAIT = 1000;

  const svg = (body) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">${body}</svg>`;

  const ICONS = {
    grid: svg(`<path d="M3 8h18M3 16h18M8 3v18M16 3v18"/>`),
    light: svg(
      `<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>`,
    ),
    dark: svg(`<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/>`),
    og: svg(`<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 16l5-5 4 4 3-3 6 6"/>`),
    close: svg(`<path d="M5 5l14 14M19 5L5 19"/>`),
  };

  // A private window or blocked site data can refuse these: the menu then works for this page and forgets.
  const read = (key) => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  };

  const write = (key, value) => {
    try {
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, value);
    } catch {}
  };

  // Tokens follow color-scheme, but an image can't: the rules and sources that swap one ask the system. Everyone else's page never
  // needs another answer, so the stylesheet stays as it is, and here they get a query that's always true, or never.
  const rules = [...document.querySelector('link[href*="main.css"]').sheet.cssRules]
    .filter((x) => x.media?.mediaText === DARK)
    .map((x) => x.media);
  const sources = document.querySelectorAll(`source[media="${DARK}"]`);

  const force = (theme) => {
    const media = { light: "not all", dark: "all" }[theme] ?? DARK;

    rules.forEach((x) => (x.mediaText = media));
    sources.forEach((x) => (x.media = media));

    if (theme === "auto") delete root.dataset.theme;
    else root.dataset.theme = theme;
  };

  const setParam = (open) => {
    const url = new URL(location.href);

    if (open) url.searchParams.set("debug", "1");
    else url.searchParams.delete("debug");

    history.replaceState(history.state, "", url);
  };

  // A line at y = N * --row from the page top, over everything.
  const grid = document.createElement("div");

  grid.hidden = true;
  grid.style.cssText = `
    position: absolute;
    z-index: 3;
    inset: 0;
    pointer-events: none;
    background: linear-gradient(rgb(0 119 204 / 0.6) 1px, transparent 1px) 0 0 / 100% var(--row);
  `;

  const panel = document.createElement("div");
  panel.className = "debug";

  const label = (el, text) => {
    el.title = text;
    el.setAttribute("aria-label", text);
  };

  // the corner's presses, and when the last five opened the menu
  let presses = [];
  let opened = -Infinity;

  const add = (text, icon, onclick) => {
    const el = document.createElement("button");

    el.type = "button";
    el.innerHTML = icon;
    label(el, text);

    // The fifth tap opens the menu on its pointerdown and puts a button under the finger, so that tap's click and the next ones'
    // land on it: the buttons wait a moment. A click leaves the focus here, and the next key would draw the ring.
    el.onclick = (e) => {
      if (e.timeStamp - opened < OPEN_WAIT) return;

      onclick();
      if (e.detail) el.blur();
    };

    panel.append(el);
    return el;
  };

  // The grid stays as it was left. A theme is forced only while the menu is open, from page to page with it, and only light or dark:
  // with none, the page shows the system's.
  let gridOn = read("debug-grid") !== "0";
  let theme = ["light", "dark"].includes(read("debug-theme")) ? read("debug-theme") : null;

  const shown = () => theme ?? (matchMedia(DARK).matches ? "dark" : "light");

  const closeMenu = () => {
    theme = null;
    write("debug-theme", null);
    write("debug", null);
    setParam(false);
    force("auto");
    grid.remove();
    panel.remove();
    root.style.position = "";
    presses = [];
  };

  const show = () => {
    grid.hidden = !gridOn;
    gridButton.setAttribute("aria-pressed", gridOn);
    themeButton.innerHTML = ICONS[shown()];
    label(themeButton, `Theme: ${shown()}`);
    force(theme ?? "auto");
  };

  const gridButton = add("Grid", ICONS.grid, () => {
    gridOn = !gridOn;
    write("debug-grid", gridOn ? "1" : "0");
    show();
  });

  const themeButton = add("Theme", ICONS[shown()], () => {
    theme = shown() === "dark" ? "light" : "dark";
    write("debug-theme", theme);
    show();
  });

  // with no theme forced, the button shows the system's, which can change under it
  matchMedia(DARK).addEventListener("change", () => {
    if (panel.isConnected) show();
  });

  // The tag holds the site's address: the same path here, so a local page shows its local card.
  add("OG preview", ICONS.og, () => {
    const card = document.querySelector('meta[property="og:image"]').content;

    open(new URL(card).pathname, "_blank", "noopener");
  });

  add("Close", ICONS.close, closeMenu);

  const openMenu = () => {
    write("debug", "1");
    setParam(true);
    root.style.position = "relative";
    document.body.append(grid, panel);
    show();
    presses = [];
  };

  // The corner is two rows square: close and the OG card on its bottom row when open.
  const corner = () => parseFloat(getComputedStyle(root).getPropertyValue("--row")) * 2;

  // By coordinates, with no element in the corner while the menu is closed. A link or button in it, the menu's own too, takes its
  // clicks as ever, so the press that closes the menu doesn't count to reopen it; the empty rest of the corner takes its own: they
  // select no text and move no focus. What's under the point, not the press's target: a phone snaps a tap near a link onto it.
  // Pointerdown, because iOS sends no click for what isn't a link. Past clientWidth is a classic scrollbar; innerHeight, not
  // clientHeight, follows a phone's toolbar as the fixed menu does.
  const inCorner = (e) =>
    e.clientX <= root.clientWidth &&
    root.clientWidth - e.clientX <= corner() &&
    innerHeight - e.clientY <= corner() &&
    !document.elementFromPoint(e.clientX, e.clientY)?.closest("a, button");

  // The click after a press the corner took goes too, wherever a snapped tap puts it. A key's click or a script's has no press
  // before it, and no detail.
  let took = false;

  document.addEventListener(
    "click",
    (e) => {
      if (!took || !e.detail) return;

      took = false;
      e.preventDefault();
      e.stopPropagation();
    },
    true,
  );

  document.addEventListener("pointerdown", (e) => {
    took = inCorner(e);
    if (!took) return;

    e.preventDefault();
    presses = [...presses, e.timeStamp].filter((x) => e.timeStamp - x < PRESS_WINDOW);
    if (presses.length < PRESSES) return;

    // open, the corner's empty part closes the menu as it opened it
    if (panel.isConnected) return closeMenu();

    opened = e.timeStamp;
    openMenu();
  });

  if (new URLSearchParams(location.search).get("debug") === "1" || read("debug") === "1")
    openMenu();
})();
