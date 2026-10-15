// SPA navigation: same-origin page links load without a full refresh.
// Falls back to normal navigation when fetch fails (e.g. opened via file://).
// Page scripts re-execute per visit (cache-busted import) and register
// interval/listener cleanup on window.__spaCleanups, which runs before swap.
const MODULE_BY_PAGE = {
  "index.html": "landing",
  "sign-in.html": "sign-in",
  "sign-up.html": "sign-up",
  "verify-email.html": "verify-email",
  "sign-up-done.html": "sign-up-done",
  "dashboard.html": "dashboard",
  "election.html": "election",
  "my-receipts.html": "my-receipts",
  "verify-receipt.html": "verify-receipt",
  "results.html": "results",
  "profile.html": "profile",
};

let navId = 0;
let lucideLoading = null;

function pageName(pathname) {
  const file = pathname.split("/").pop() || "index.html";
  return MODULE_BY_PAGE[file] ?? null;
}

function ensureLucide() {
  if (window.lucide) {
    window.lucide.createIcons();
    return Promise.resolve();
  }
  if (!document.querySelector("[data-lucide]")) return Promise.resolve();
  lucideLoading ??= new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = "https://unpkg.com/lucide@latest";
    script.onload = () => {
      if (window.lucide) window.lucide.createIcons();
      resolve();
    };
    script.onerror = () => resolve();
    document.head.appendChild(script);
  });
  return lucideLoading;
}

function runCleanups() {
  const cleanups = window.__spaCleanups;
  if (Array.isArray(cleanups)) {
    cleanups.splice(0).forEach((fn) => {
      try {
        fn();
      } catch {
        // Cleanup is best-effort.
      }
    });
  }
}

// Rewrite relative href/src against the fetched URL so injected markup
// resolves assets and links correctly from any current location.
function resolveRelativeUrls(doc, base) {
  doc.querySelectorAll("[href],[src]").forEach((el) => {
    for (const attr of ["href", "src"]) {
      const value = el.getAttribute(attr);
      if (!value || value.startsWith("#") || /^[a-z][a-z0-9+.-]*:/i.test(value)) continue;
      el.setAttribute(attr, new URL(value, base).href);
    }
  });
}

function currentStylesheets() {
  return [...document.querySelectorAll('link[rel="stylesheet"]')];
}

function absoluteHref(link) {
  return new URL(link.getAttribute("href"), document.baseURI).href;
}

function syncStylesheets(doc) {
  const wanted = [...doc.querySelectorAll('link[rel="stylesheet"]')]
    .map((link) => new URL(link.getAttribute("href"), doc.baseURI).href);
  currentStylesheets().forEach((link) => {
    if (!wanted.includes(absoluteHref(link))) link.remove();
  });
  wanted.forEach((href) => {
    const exists = currentStylesheets().some((link) => absoluteHref(link) === href);
    if (!exists) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      document.head.appendChild(link);
    }
  });
}

function syncMeta(doc) {
  const next = doc.querySelector('meta[name="description"]');
  const current = document.querySelector('meta[name="description"]');
  if (next && current) current.setAttribute("content", next.getAttribute("content") ?? "");
}

async function bootPage(url) {
  const name = pageName(new URL(url, location.href).pathname);
  if (!name) return;
  navId += 1;
  await import(new URL(`../pages/${name}.js?spa=${navId}`, import.meta.url));
  await ensureLucide();
}

async function navigate(url, { push = true } = {}) {
  const target = new URL(url, location.href);
  runCleanups();
  let html;
  try {
    const response = await fetch(target.href);
    if (!response.ok) throw new Error("bad status");
    html = await response.text();
  } catch {
    location.href = target.href; // fallback: full page load
    return;
  }
  const doc = new DOMParser().parseFromString(html, "text/html");
  resolveRelativeUrls(doc, target.href);
  syncStylesheets(doc);
  syncMeta(doc);
  document.title = doc.title;
  document.body.innerHTML = doc.body.innerHTML;
  if (push) history.pushState({}, "", target.href);
  await bootPage(target.href);
  if (target.hash) {
    document.querySelector(target.hash)?.scrollIntoView();
  } else {
    window.scrollTo(0, 0);
  }
  const heading = document.querySelector("h1");
  if (heading) {
    heading.setAttribute("tabindex", "-1");
    heading.focus({ preventScroll: true });
  }
}

document.addEventListener("click", (event) => {
  if (event.defaultPrevented || event.button !== 0) return;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const anchor = event.target instanceof Element ? event.target.closest("a[href]") : null;
  if (!anchor || anchor.target || anchor.hasAttribute("download")) return;
  const href = anchor.getAttribute("href");
  if (!href || href.startsWith("#")) return;
  const target = new URL(href, location.href);
  if (target.origin !== location.origin) return;
  if (target.pathname === location.pathname) return; // same-page anchors jump natively
  if (!/\.html?$/.test(target.pathname)) return; // unknown targets load normally
  event.preventDefault();
  navigate(target.href);
});

window.addEventListener("popstate", () => {
  navigate(location.href, { push: false });
});

// Boot the page we landed on (covers full loads and back/forward).
bootPage(location.href);
