#!/usr/bin/env node

import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";

const DEFAULT_BASE_URL = "http://localhost:1111";
const DEFAULT_TOLERANCE = 0.75;
const DEFAULT_PUBLIC_DIR = "public";

const PAGES = ["/rhythm-fixture/", "/coding-agents-statusline/", "/tags", "/404.html"];

const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844, deviceScaleFactor: 1 },
  { name: "mobile-wide", width: 560, height: 900, deviceScaleFactor: 1 },
  { name: "tablet", width: 768, height: 1024, deviceScaleFactor: 1 },
  { name: "desktop", width: 1280, height: 900, deviceScaleFactor: 1 },
  { name: "fractional-dpr", width: 1109, height: 971, deviceScaleFactor: 1.5 },
];

const BLOCK_SELECTOR = [
  "body > header",
  "body > footer",
  "main > h1",
  "main > h2",
  "main > h3",
  "main > h4",
  "main > h5",
  "main > h6",
  "main > p",
  "main > ul",
  "main > ol",
  "main > blockquote",
  "main > pre",
  "main > table",
  "main > hr",
  "main > .posts-list",
  "main > .posts-list > li",
  "article.post",
  "article.post > header",
  "article.post > h1",
  "article.post > h2",
  "article.post > h3",
  "article.post > h4",
  "article.post > h5",
  "article.post > h6",
  "article.post > p",
  "article.post > ul",
  "article.post > ol",
  "article.post > blockquote",
  "article.post > pre",
  "article.post > table",
  "article.post > hr",
  "article.post > .rhythm-media",
  ".social-share",
].join(",");

const parseArgs = () => {
  const args = process.argv.slice(2);
  const options = {
    baseUrl: process.env.RHYTHM_BASE_URL || DEFAULT_BASE_URL,
    tolerance: Number(process.env.RHYTHM_TOLERANCE || DEFAULT_TOLERANCE),
    pages: [...PAGES],
    debugGrid: false,
    headed: false,
    servePublic: false,
    publicDir: DEFAULT_PUBLIC_DIR,
  };

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    const next = args[i + 1];

    if (arg === "--") {
      continue;
    } else if (arg === "--base-url" && next) {
      options.baseUrl = next;
      i += 1;
    } else if (arg === "--page" && next) {
      options.pages = [next];
      i += 1;
    } else if (arg === "--pages" && next) {
      options.pages = next
        .split(",")
        .map((page) => page.trim())
        .filter(Boolean);
      i += 1;
    } else if (arg === "--tolerance" && next) {
      options.tolerance = Number(next);
      i += 1;
    } else if (arg === "--debug-grid") {
      options.debugGrid = true;
    } else if (arg === "--headed") {
      options.headed = true;
    } else if (arg === "--serve-public") {
      options.servePublic = true;
      if (next && !next.startsWith("--")) {
        options.publicDir = next;
        i += 1;
      }
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!Number.isFinite(options.tolerance)) {
    throw new Error(`Invalid tolerance: ${options.tolerance}`);
  }

  return options;
};

const CONTENT_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".xml": "application/xml; charset=utf-8",
};

const resolvePublicPath = async (root, requestPath) => {
  const decodedPath = decodeURIComponent(requestPath.split("?")[0]);
  const normalizedPath = path.normalize(decodedPath).replace(/^(\.\.[/\\])+/, "");
  const safePath = normalizedPath === "/" ? "/index.html" : normalizedPath;
  const directPath = path.join(root, safePath);
  const relativePath = path.relative(root, directPath);

  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    return path.join(root, "404.html");
  }

  try {
    const directStat = await stat(directPath);
    if (directStat.isDirectory()) return path.join(directPath, "index.html");
    return directPath;
  } catch {
    if (!path.extname(directPath)) {
      const htmlPath = `${directPath}.html`;
      try {
        await stat(htmlPath);
        return htmlPath;
      } catch {
        return path.join(root, "404.html");
      }
    }

    return path.join(root, "404.html");
  }
};

const startStaticServer = async (publicDir) => {
  const root = path.resolve(publicDir);
  let baseUrl = "";

  const server = createServer(async (req, res) => {
    try {
      const filePath = await resolvePublicPath(root, req.url || "/");
      let body = await readFile(filePath);
      const ext = path.extname(filePath);
      const contentType = CONTENT_TYPES[ext] || "application/octet-stream";

      if (ext === ".html") {
        body = Buffer.from(body.toString("utf8").replaceAll("https://vladkens.cc/", `${baseUrl}/`));
      }

      res.writeHead(filePath.endsWith("404.html") ? 404 : 200, {
        "content-type": contentType,
      });
      res.end(body);
    } catch (error) {
      res.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
      res.end(String(error));
    }
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));

  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("Failed to start static server");
  }

  baseUrl = `http://127.0.0.1:${address.port}`;

  return {
    baseUrl,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
};

const loadPlaywright = async () => {
  try {
    return await import("playwright");
  } catch {
    console.error("Playwright is not installed.");
    console.error("Install it with: pnpm add -D playwright");
    console.error("Then run: pnpm exec playwright install chromium");
    process.exit(2);
  }
};

const formatUrl = (baseUrl, pathname, debugGrid) => {
  const url = new URL(pathname, baseUrl);
  if (debugGrid) url.searchParams.set("debug", "1");
  return url.toString();
};

const waitForLayout = async (page) => {
  await page.waitForLoadState("domcontentloaded");

  const waitForAssets = async () => {
    await page.evaluate(async () => {
      if (document.fonts?.ready) await document.fonts.ready;

      await Promise.all(
        [...document.images].map((img) => {
          if (img.complete) return undefined;
          return new Promise((resolve) => {
            img.addEventListener("load", resolve, { once: true });
            img.addEventListener("error", resolve, { once: true });
          });
        }),
      );
    });
  };

  await waitForAssets();

  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;

    const maxY = document.documentElement.scrollHeight - window.innerHeight;
    const step = Math.max(200, Math.floor(window.innerHeight * 0.8));

    for (let y = 0; y <= maxY; y += step) {
      window.scrollTo(0, y);
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    }

    window.scrollTo(0, document.documentElement.scrollHeight);
  });

  if (await page.locator("script[src*='giscus.app']").count()) {
    await page
      .locator("iframe.giscus-frame")
      .waitFor({ state: "attached", timeout: 5000 })
      .catch(() => undefined);
  }

  await waitForAssets();
  await page.waitForTimeout(150);
  await page.evaluate(() => window.scrollTo(0, 0));
};

const collectRhythmFailures = async (page, tolerance) =>
  page.evaluate(
    ({ selector, tolerance }) => {
      const line = Number.parseFloat(getComputedStyle(document.body).lineHeight) || 24;
      const doc = document.documentElement;

      const offset = (value) => {
        const raw = ((value % line) + line) % line;
        return Math.min(raw, line - raw);
      };

      const cssPath = (el) => {
        const parts = [];
        let node = el;

        while (node && node.nodeType === Node.ELEMENT_NODE && node !== document.body) {
          const tag = node.tagName.toLowerCase();
          const id = node.id ? `#${node.id}` : "";
          const className =
            typeof node.className === "string" && node.className.trim()
              ? `.${node.className.trim().split(/\s+/).slice(0, 3).join(".")}`
              : "";

          let nth = "";
          if (!id && node.parentElement) {
            const siblings = [...node.parentElement.children].filter(
              (child) => child.tagName === node.tagName,
            );
            if (siblings.length > 1) nth = `:nth-of-type(${siblings.indexOf(node) + 1})`;
          }

          parts.unshift(`${tag}${id}${className}${nth}`);
          node = node.parentElement;
        }

        return parts.join(" > ");
      };

      const allBlocks = [...document.querySelectorAll(selector)].filter((el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);

        return rect.width > 0 && rect.height > 0 && style.display !== "none";
      });

      const failures = allBlocks
        .map((el, index) => {
          const rect = el.getBoundingClientRect();
          const top = rect.top + window.scrollY;
          const bottom = rect.bottom + window.scrollY;
          const checks = {
            top: offset(top),
            height: offset(rect.height),
            bottom: offset(bottom),
          };

          const maxOffset = Math.max(checks.top, checks.height, checks.bottom);

          return {
            index,
            selector: cssPath(el),
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 120),
            top: Number(top.toFixed(2)),
            height: Number(rect.height.toFixed(2)),
            bottom: Number(bottom.toFixed(2)),
            offsets: {
              top: Number(checks.top.toFixed(2)),
              height: Number(checks.height.toFixed(2)),
              bottom: Number(checks.bottom.toFixed(2)),
            },
            maxOffset: Number(maxOffset.toFixed(2)),
          };
        })
        .filter((item) => item.maxOffset > tolerance);

      return {
        line,
        checked: allBlocks.length,
        failures,
        horizontalOverflow: doc.scrollWidth - doc.clientWidth,
        documentHeight: doc.scrollHeight,
      };
    },
    { selector: BLOCK_SELECTOR, tolerance },
  );

const run = async () => {
  const options = parseArgs();
  const staticServer = options.servePublic ? await startStaticServer(options.publicDir) : null;
  if (staticServer) options.baseUrl = staticServer.baseUrl;

  let browser;
  const failures = [];

  try {
    const { chromium } = await loadPlaywright();
    browser = await chromium.launch({ headless: !options.headed });

    for (const viewport of VIEWPORTS) {
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        deviceScaleFactor: viewport.deviceScaleFactor,
      });

      for (const pathname of options.pages) {
        const page = await context.newPage();
        const url = formatUrl(options.baseUrl, pathname, options.debugGrid);

        try {
          await page.goto(url, { waitUntil: "domcontentloaded" });
          await waitForLayout(page);

          const report = await collectRhythmFailures(page, options.tolerance);
          const pageFailures = [];

          if (report.horizontalOverflow > options.tolerance) {
            pageFailures.push({
              selector: "document",
              text: "Horizontal page overflow",
              top: 0,
              height: 0,
              bottom: 0,
              offsets: { top: 0, height: report.horizontalOverflow, bottom: 0 },
              maxOffset: report.horizontalOverflow,
            });
          }

          pageFailures.push(...report.failures);

          if (pageFailures.length > 0) {
            failures.push({
              page: pathname,
              url,
              viewport,
              line: report.line,
              checked: report.checked,
              failures: pageFailures,
            });
          } else {
            console.log(
              `ok ${viewport.name.padEnd(14)} ${pathname.padEnd(32)} checked=${report.checked} line=${report.line}`,
            );
          }
        } finally {
          await page.close();
        }
      }

      await context.close();
    }
  } finally {
    await browser?.close();
    await staticServer?.close();
  }

  if (failures.length === 0) return;

  console.error("");
  console.error(`Vertical rhythm check failed (${failures.length} page/viewport pairs).`);

  for (const group of failures) {
    const label = `${group.viewport.name} ${group.viewport.width}x${group.viewport.height}@${group.viewport.deviceScaleFactor}`;
    console.error("");
    console.error(`${group.page} (${label}, line=${group.line}, checked=${group.checked})`);

    for (const failure of group.failures.slice(0, 20)) {
      console.error(
        `  ${failure.selector}\n` +
          `    text: ${failure.text || "<empty>"}\n` +
          `    top=${failure.top} height=${failure.height} bottom=${failure.bottom}\n` +
          `    offsets: top=${failure.offsets.top} height=${failure.offsets.height} bottom=${failure.offsets.bottom}`,
      );
    }

    if (group.failures.length > 20) {
      console.error(`  ...and ${group.failures.length - 20} more`);
    }
  }

  process.exit(1);
};

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
