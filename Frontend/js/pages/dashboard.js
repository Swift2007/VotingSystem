// Dashboard overview: GET /elections via services/, rendered into the same
// .election-cards as the static demo HTML. When the backend is missing
// (network error), demo cards stay untouched so the page still previews.
// Receipt handoff uses sessionStorage (never the URL) via delegation,
// so dynamically rendered links work too.
import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";
import { listElections } from "../../services/elections.service.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

// Delegated: covers both static demo links and API-rendered ones.
document.addEventListener("click", (event) => {
  const link = event.target instanceof Element ? event.target.closest("[data-code]") : null;
  if (!link || !(link instanceof HTMLElement)) return;
  try {
    window.sessionStorage.setItem("votex-verify-code", link.dataset.code ?? "");
  } catch {
    // Non-essential convenience only.
  }
});

/** Status → pill class + action link for one election card. */
function electionChrome(status) {
  if (status === "open") return { pill: "pill-counted", label: "Open", action: "Vote now", href: "./election.html", primary: true };
  if (status === "upcoming") return { pill: "pill-recorded", label: "Upcoming", action: "", href: "", primary: false };
  return { pill: "pill-closed", label: "Closed", action: "View results", href: "./results.html", primary: false };
}

/** Build one .election-card from an API item (textContent only). */
function electionCard(item) {
  const status = String(item?.status ?? "upcoming").toLowerCase();
  const chrome = electionChrome(status);

  const li = document.createElement("li");
  li.className = "election-card";

  const head = document.createElement("div");
  const h3 = document.createElement("h3");
  h3.textContent = item?.title ?? "Election";
  const meta = document.createElement("p");
  meta.className = "receipt-meta";
  meta.textContent = item?.meta ?? item?.closes_at ?? item?.subtitle ?? "";
  head.append(h3, meta);

  const side = document.createElement("div");
  side.className = "election-side";
  const pill = document.createElement("span");
  pill.className = `pill ${chrome.pill}`;
  pill.textContent = item?.status_label ?? chrome.label;
  side.appendChild(pill);

  if (chrome.action) {
    const link = document.createElement("a");
    link.className = `button ${chrome.primary ? "button-primary" : "button-outline"} button-small`;
    link.href = chrome.href;
    link.textContent = chrome.action;
    side.appendChild(link);
  }

  li.append(head, side);
  return li;
}

/** Update the three stat tiles from API counts (skips tiles that are missing). */
function paintStats(items) {
  const tiles = document.querySelectorAll(".stats-grid .stat-card .stat-value");
  if (tiles.length < 3) return;
  const by = (s) => items.filter((e) => String(e?.status ?? "").toLowerCase() === s).length;
  // Order in dashboard.html: Open elections, Votes cast, Upcoming.
  // Votes-cast has no elections endpoint yet — only open/upcoming refresh.
  if (tiles[0]) tiles[0].textContent = String(by("open"));
  if (tiles[2]) tiles[2].textContent = String(by("upcoming"));
}

// API-first: replace demo cards only when the backend answers.
// Expected: an array, or { elections: [...] }. Anything else keeps demo HTML.
try {
  const data = await listElections();
  const items = Array.isArray(data) ? data : data?.elections;
  const list = document.querySelector(".election-cards");
  if (Array.isArray(items) && items.length > 0 && list) {
    list.textContent = "";
    for (const item of items) list.appendChild(electionCard(item));
    paintStats(items);
    refreshIcons();
  }
} catch {
  // status 0 (backend missing/offline): static demo HTML remains as preview.
}
