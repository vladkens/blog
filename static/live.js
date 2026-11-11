// The dev server's live update: base.html adds this file only under --debug, so the build never has it. It asks /_live for
// a hash of the files about once a second while the tab is shown. New Markdown swaps the article in place, new CSS swaps
// the stylesheets, and anything else reloads the page where it was. Runs after main.js and calls its init functions.
(() => {
  const SCROLL = "live-scroll";
  const EVERY = 1000;

  let seen; // the hashes and server this page was made with, from the first answer
  let down = false;

  // MARK: scroll
  // A reload comes back where it was, the same page only. The browser's own restoring would race this one, so it is off for
  // that reload alone, and back and forward keep theirs.
  try {
    const at = JSON.parse(sessionStorage.getItem(SCROLL));
    sessionStorage.removeItem(SCROLL);

    if (at?.path === location.pathname) scrollTo({ top: at.y, behavior: "instant" });
  } catch {}

  history.scrollRestoration = "auto";

  const reload = () => {
    try {
      sessionStorage.setItem(SCROLL, JSON.stringify({ path: location.pathname, y: scrollY }));
      history.scrollRestoration = "manual";
    } catch {}

    location.reload();
  };

  // MARK: styles
  // The new sheet goes in beside the old one, which leaves once it has loaded, so the page never shows unstyled.
  const restyle = (stamp) => {
    document.querySelectorAll('link[rel="stylesheet"]').forEach((x) => {
      const url = new URL(x.href);
      if (url.origin !== location.origin) return;

      const next = x.cloneNode();
      url.searchParams.set("t", stamp);
      next.href = url;
      next.onload = () => x.remove();
      x.after(next);
    });
  };

  // MARK: content
  // The parts of the page Markdown makes. A TOC that comes or goes changes the sheet's grid, so that one reloads.
  const PARTS = [".head", ".toc", "article"];

  const swap = async () => {
    const rep = await fetch(location.href, { cache: "no-store" });
    if (!rep.ok) {
      console.log(`live: ${location.pathname} answered ${rep.status}, waiting for the next save`);
      return;
    }

    const doc = new DOMParser().parseFromString(await rep.text(), "text/html");
    const olds = PARTS.map((x) => document.querySelector(x));
    const news = PARTS.map((x) => doc.querySelector(x));
    if (olds.some((x, i) => !x !== !news[i])) return reload();

    const y = scrollY;
    olds.forEach((x, i) => x?.replaceWith(document.adoptNode(news[i])));
    document.querySelector(".sheet").style.cssText = doc.querySelector(".sheet").style.cssText;
    document.title = doc.title;

    initWallets();
    initCode();
    initZoom();

    const toc = document.querySelector(".toc");
    if (toc) initToc(toc);

    scrollTo({ top: y, behavior: "instant" });
  };

  // MARK: poll
  const poll = async () => {
    let now;
    try {
      now = await (await fetch("/_live", { cache: "no-store" })).json();
    } catch {
      // Flask restarting after a .py change: one line, then quiet until it answers
      if (!down) console.log("live: dev server is down, waiting");
      down = true;
      return;
    }

    down = false;
    const last = seen ?? now;

    // A new server, or a template or script. The page is asked for first: a server still going down would leave the
    // browser's error page, without this file. Unanswered, the change waits for the next poll; an error page, for the
    // next save.
    if (now.boot !== last.boot || now.code !== last.code) {
      const rep = await fetch(location.href, { cache: "no-store" }).catch(() => null);
      if (!rep) return;

      seen = now;
      if (rep.ok) return reload();

      console.log(`live: ${location.pathname} answered ${rep.status}, waiting for the next save`);
      return;
    }

    seen = now;
    if (now.styles !== last.styles) restyle(now.styles);
    if (now.content !== last.content) await swap();
  };

  const loop = async () => {
    // a failed swap waits for the next save, as a page error does
    if (!document.hidden) await poll().catch((e) => console.log(`live: ${e}`));

    setTimeout(loop, EVERY);
  };

  loop();
})();
