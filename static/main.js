// MARK: toast
// One element for every copy. It stands in the page from the start, or a screen reader would miss the first message, and it
// empties once faded, so a search of the page finds nothing there.
const toast = document.createElement("div");
let toastTimer;

toast.className = "toast";
toast.setAttribute("role", "status");
toast.ontransitionend = () => {
  if (!toast.classList.contains("shown")) toast.textContent = "";
};
document.body.append(toast);

const notifyCopied = () => {
  toast.textContent = document.documentElement.lang === "ru" ? "Скопировано" : "Copied";
  toast.classList.add("shown");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("shown"), 1500);
};

// MARK: wallets
// Made a button here, so a page without JS has no dead one. A refused copy rejects before the toast, so it claims nothing.
const initWallets = () =>
  document.querySelectorAll(".wallets-list code").forEach((x) => {
    x.tabIndex = 0;
    x.title = document.documentElement.lang === "ru" ? "Скопировать" : "Click to copy";
    x.setAttribute("role", "button");

    x.onclick = async (e) => {
      // a click leaves the focus here, and the next key would draw the ring
      if (e.detail) x.blur();

      await navigator.clipboard.writeText(x.textContent);
      notifyCopied();
    };

    x.onkeydown = (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;

      e.preventDefault();
      x.click();
    };
  });

initWallets();

// MARK: copy
// Icons from: https://www.untitledui.com/icon/copy-06 https://www.untitledui.com/icon/check
const CopyIcon = `
<svg
    width="100%"
    height="100%"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M7.5 3H14.6C16.8402 3 17.9603 3 18.816 3.43597C19.5686 3.81947 20.1805 4.43139 20.564 5.18404C21 6.03969 21 7.15979 21 9.4V16.5M6.2 21H14.3C15.4201 21 15.9802 21 16.408 20.782C16.7843 20.5903 17.0903 20.2843 17.282 19.908C17.5 19.4802 17.5 18.9201 17.5 17.8V9.7C17.5 8.57989 17.5 8.01984 17.282 7.59202C17.0903 7.21569 16.7843 6.90973 16.408 6.71799C15.9802 6.5 15.4201 6.5 14.3 6.5H6.2C5.0799 6.5 4.51984 6.5 4.09202 6.71799C3.71569 6.90973 3.40973 7.21569 3.21799 7.59202C3 8.01984 3 8.57989 3 9.7V17.8C3 18.9201 3 19.4802 3.21799 19.908C3.40973 20.2843 3.71569 20.5903 4.09202 20.782C4.51984 21 5.0799 21 6.2 21Z"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
</svg>
`.trim();

const CheckIcon = `
<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
 <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
`.trim();

// Added here, so a feed and a page without JS have no dead button.
const initCode = () =>
  document.querySelectorAll(".code").forEach((box) => {
    const el = document.createElement("button");
    let timer;

    el.setAttribute(
      "aria-label",
      document.documentElement.lang === "ru" ? "Скопировать код" : "Copy code",
    );
    el.innerHTML = CopyIcon;

    el.onclick = async (e) => {
      await navigator.clipboard.writeText(box.querySelector("code").textContent);
      notifyCopied();

      el.innerHTML = CheckIcon;
      el.classList.add("copied");
      clearTimeout(timer);

      timer = setTimeout(() => {
        el.innerHTML = CopyIcon;
        el.classList.remove("copied");
      }, 1500);

      // a click leaves the focus here, and the next key would draw the ring
      if (e.detail) el.blur();
    };

    box.append(el);
  });

initCode();

// MARK: zoom
// Pictures in the text, one at a time: a click, a tap or Enter shows a copy over the page, and a click, Esc or a scroll puts
// it back. A logo is a mark, and an image in a link goes where the link goes. The browser's view transition carries the
// picture between its place and the copy, so nothing here measures it; without one, or with reduced motion, it just swaps.
// The listeners are the document's, set once: a new article from the dev server only needs its pictures marked.
const ZOOMED = 'article img:not(.logo, [alt="logo"], a img)';
const still = matchMedia("(prefers-reduced-motion: reduce)");
let zoomed; // the open one: { img, box, y, keyboard }
let running; // the transition under way, if any

// Settles either way: a transition the next one cuts short rejects `ready`, and that is no error.
const transition = (update) => {
  if (!document.startViewTransition || still.matches) return Promise.resolve(update());

  const x = document.startViewTransition(update);
  running = x;
  x.ready.catch(() => {});

  return x.finished
    .catch(() => {})
    .finally(() => {
      if (running === x) running = null;
    });
};

const openZoom = (img, keyboard) => {
  const box = document.createElement("div");
  const copy = img.cloneNode();

  copy.classList.remove("zoomable");
  copy.removeAttribute("tabindex");
  box.className = "zoom";
  box.tabIndex = -1;
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-modal", "true");
  box.setAttribute("aria-label", img.alt);
  box.append(copy);
  zoomed = { img, box, y: scrollY, keyboard };

  // the picture's place is where the transition starts, the copy where it ends
  img.style.viewTransitionName = "zoom";
  transition(async () => {
    img.style.removeProperty("view-transition-name");
    document.body.append(box);
    box.focus({ preventScroll: true });
    await copy.decode().catch(() => {});
  });
};

const closeZoom = () => {
  const { img, box, keyboard } = zoomed;
  zoomed = null;

  transition(() => {
    box.remove();
    img.style.viewTransitionName = "zoom";
    if (keyboard) img.focus({ preventScroll: true });
  }).finally(() => img.style.removeProperty("view-transition-name"));
};

const initZoom = () => {
  zoomed?.box.remove(); // the article it came from is gone
  zoomed = null;

  document.querySelectorAll(ZOOMED).forEach((x) => {
    x.classList.add("zoomable");
    x.tabIndex = 0;
  });
};

// The transition lets clicks through to the page under it (main.css). A click while it opens closes it, and one while it
// closes acts on where it ends.
document.addEventListener("click", (e) => {
  const opening = zoomed && running;
  running?.skipTransition();

  if (zoomed) {
    if (opening || zoomed.box.contains(e.target)) closeZoom();
    return;
  }

  if (!e.target.classList?.contains("zoomable")) return;

  // a click leaves the focus there, and the next key would draw the ring
  if (e.detail) e.target.blur();
  openZoom(e.target, !e.detail);
});

// Space is left to scroll the page. Tab closes too, or it would walk the page under the copy.
document.addEventListener("keydown", (e) => {
  if (zoomed) {
    if (!["Escape", "Enter", " ", "Tab"].includes(e.key)) return;

    e.preventDefault();
    closeZoom();
    return;
  }

  if (e.key !== "Enter" || !e.target.classList?.contains("zoomable")) return;

  e.preventDefault();
  openZoom(e.target, true);
});

addEventListener(
  "scroll",
  () => {
    if (zoomed && Math.abs(scrollY - zoomed.y) > 40) closeZoom();
  },
  { passive: true },
);

initZoom();

// MARK: comments
// giscus, fetched a screen before the reader gets there. Its frame reports its height as it loads: a spinner first, then the
// thread. The spinner's report counts for nothing. The block grows with the frame, at once, or the frame would show clipped, and
// shrinks only once the reports settle; in whole rows either way, so the footer below stays on a line and the page moves at most
// once. The frame shows once the thread's height settles, or after a wait, so a frame that never reports isn't lost.
const SETTLE = 150; // ms without a new report
const SPINNER = 160; // px: giscus's loading state reports less, a thread more
const GIVE_UP = 5000; // ms

const initComments = (box) => {
  const { client, ...config } = box.dataset;
  const origin = new URL(client).origin;
  const dark = matchMedia("(prefers-color-scheme: dark)");
  const theme = () => document.documentElement.dataset.theme ?? (dark.matches ? "dark" : "light");
  const row = () =>
    parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--row"));

  let shown = theme();
  let frame; // set by its first report: until then the iframe holds a blank document, which refuses the message
  let settle;

  const reveal = () => box.classList.add("ready");
  const fit = (height) => box.style.setProperty("--rows", Math.ceil(height / row()));

  const sync = () => {
    if (!frame || shown === theme()) return;

    shown = theme();
    frame.postMessage({ giscus: { setConfig: { theme: shown } } }, origin);
  };

  const load = () => {
    const script = document.createElement("script");

    shown = theme();
    script.src = client;
    script.async = true;
    script.crossOrigin = "anonymous";
    Object.assign(script.dataset, config, { theme: shown });
    box.append(script);
    setTimeout(reveal, GIVE_UP);
  };

  window.addEventListener("message", (e) => {
    const height = e.origin === origin && e.data?.giscus?.resizeHeight;
    if (!height) return;

    frame = e.source;
    sync(); // a change that came while the frame was still loading

    if (height <= SPINNER && !box.classList.contains("ready")) return;

    if (height > box.offsetHeight) fit(height);
    clearTimeout(settle);
    settle = setTimeout(() => {
      fit(height);
      reveal();
    }, SETTLE);
  });

  dark.addEventListener("change", sync);
  new MutationObserver(sync).observe(document.documentElement, { attributeFilter: ["data-theme"] });

  const seen = new IntersectionObserver(
    ([x]) => {
      if (!x.isIntersecting) return;

      seen.disconnect();
      load();
    },
    { rootMargin: "100% 0px" },
  );

  // Back from GitHub sign-in with the session in the URL: only the client takes it out, so it doesn't wait for the scroll.
  if (new URLSearchParams(location.search).has("giscus")) load();
  else seen.observe(box);
};

const comments = document.querySelector(".comments");
if (comments) initComments(comments);

// MARK: toc
// The section at the reading line is current and those above it are read. --at is how far the reader is, in entries: the
// intro inks the half row down to the first notch, each section the row from its notch to the next, and the last one down
// to the end of the list. A second call, from the dev server's swap of the article, drops the first one's listeners.
let tocListeners;

const initToc = (toc) => {
  tocListeners?.abort();
  tocListeners = new AbortController();
  const { signal } = tocListeners;

  const items = [...toc.querySelectorAll("li")];
  const links = items.map((x) => x.querySelector("a"));
  const heads = links.map((x) => document.getElementById(decodeURIComponent(x.hash.slice(1))));
  const article = document.querySelector("article");
  const main = document.querySelector("main");
  const figure = document.querySelector(".art figure");
  const wide = matchMedia("(width >= 1356px)"); // where the left field is whole, and the list exists
  if (heads.some((x) => !x)) return;

  // from the top of the page, whatever is positioned on the way
  const top = (el) => {
    let y = 0;
    for (; el; el = el.offsetParent) y += el.offsetTop;

    return y;
  };

  // Where things are, read again only after something changed size: the window, the page, the article, the work.
  let layout;
  let dirty = true;

  const measure = () => {
    const row = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--row"));
    const start = top(article);

    layout = {
      row,
      marks: [
        [start, 0],
        ...heads.map((x, i) => [top(x), i + 0.5]),
        [start + article.offsetHeight, items.length],
      ],
      pad: parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0,
      end: document.documentElement.scrollHeight,
      // the list where it sticks, or lower, beside the text's start, until the page scrolls it up there
      stuck: parseFloat(getComputedStyle(toc).top),
      first: top(main),
      // the list, a row of air, the work held a row over the window's bottom
      room: (items.length + 2) * row + figure.offsetHeight,
    };
    dirty = false;
  };

  // A jump to an entry makes it current until the page scrolls away from where the jump put it: near the end of a page the
  // jump can't bring its heading up to the reading line. The address's own section, on load, only if the page is there.
  let pinned = -1;
  let landed = null; // where the jump put the page, once it's there
  let loading = true;
  let frame = 0;
  let inked, current, shown;

  const update = () => {
    frame = 0;
    if (!wide.matches) return;

    if (dirty) measure();
    const { row, marks, pad, end, stuck, first, room } = layout;
    const y0 = scrollY;
    const h = innerHeight;

    // Once there, only a scroll away lets go: a page that grows after, as the comments load, moves the target, not the page.
    if (pinned >= 0 && landed === null) {
      const target = Math.min(Math.max(marks[pinned + 1][0] - pad, 0), end - h);
      if (Math.abs(y0 - target) <= 4) landed = y0;
      else if (loading) pinned = -1;
    } else if (pinned >= 0 && Math.abs(y0 - landed) > 4) {
      pinned = -1;
    }

    loading = false;

    // A row under the bar, where a jump lands a heading. Over the page's last screen of scrolling the line runs on down to
    // the window's bottom, so the short sections at the end get their turn, and the very end is the last one.
    const lead = row * 4;
    const stretch = Math.min(Math.max(1 - (end - h - y0) / h, 0), 1);
    const y = y0 + lead + (h - lead) * stretch;

    let at = y < marks[0][0] ? 0 : items.length;
    for (let i = 0; i < marks.length - 1; i++) {
      const [ya, a] = marks[i];
      const [yb, b] = marks[i + 1];
      if (y < ya || y >= yb) continue;

      at = a + ((y - ya) / (yb - ya)) * (b - a);
      break;
    }

    let now = marks.slice(1, -1).filter(([yh]) => yh <= y).length - 1;
    if (pinned >= 0) {
      now = pinned;
      at = pinned + 0.5;
    }

    // Only where the window holds the whole list, from where it is now, clear of the work: elsewhere it stays away.
    const show = Math.max(stuck, first - y0) + room <= h;
    const ink = at.toFixed(3);

    if (ink !== inked) {
      inked = ink;
      toc.style.setProperty("--at", ink);
    }

    if (now !== current) {
      current = now;
      items.forEach((x, i) => {
        x.classList.toggle("read", i < now);
        x.classList.toggle("now", i === now);

        if (i === now) links[i].setAttribute("aria-current", "location");
        else links[i].removeAttribute("aria-current");
      });
    }

    if (show !== shown) {
      shown = show;
      toc.classList.toggle("shown", show);
    }
  };

  const schedule = () => {
    frame ||= requestAnimationFrame(update);
  };

  const remeasure = () => {
    dirty = true;
    schedule();
  };

  const pin = (i) => {
    pinned = i;
    landed = null;
    schedule();
  };

  // the address's section, on load, on a jump from anywhere, and back or forward
  const pinHash = () =>
    pin(heads.findIndex((x) => `#${x.id}` === decodeURIComponent(location.hash)));

  // what only the reader does: the scroll a jump makes is none of these
  const unpin = () => {
    if (pinned >= 0) pin(-1);
  };

  toc.addEventListener("click", (e) => pin(links.indexOf(e.target.closest("a"))), { signal });
  addEventListener("hashchange", pinHash, { signal });
  for (const x of ["wheel", "touchmove", "keydown", "pointerdown"]) {
    addEventListener(x, unpin, { passive: true, signal });
  }

  addEventListener("scroll", schedule, { passive: true, signal });
  addEventListener("resize", remeasure, { signal });
  wide.addEventListener("change", remeasure, { signal });

  const sizes = new ResizeObserver(remeasure);
  [document.documentElement, article, figure].forEach((x) => sizes.observe(x));
  signal.addEventListener("abort", () => sizes.disconnect());

  pinHash();
};

const toc = document.querySelector(".toc");
if (toc) initToc(toc);
