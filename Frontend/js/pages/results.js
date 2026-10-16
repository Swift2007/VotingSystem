// Results: GET /results via services/, rendered as .result-election sections.
// Published totals only — the backend 404s open elections, which render as
// the locked "Not yet published" card. Static demo HTML stays when the
// backend is unreachable, so the page still previews offline.
import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";
import { listResults } from "../../services/results.service.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

/** Animate .bar fills from data-votes/data-total (demo + API markup share this). */
function paintBars(scope = document) {
  scope.querySelectorAll(".bar span[data-votes]").forEach((fill) => {
    const votes = Number(fill.dataset.votes) || 0;
    const total = Number(fill.dataset.total) || 1;
    requestAnimationFrame(() => {
      fill.style.width = `${Math.min(100, (votes / total) * 100)}%`;
    });
  });
}

paintBars();

/** One published election section (winner card + per-candidate bars). */
function resultSection(item) {
  const total = Number(item?.total_ballots ?? item?.total ?? 1);
  const section = document.createElement("section");
  section.className = "result-election";

  const head = document.createElement("div");
  head.className = "result-head";
  const titleWrap = document.createElement("div");
  const h2 = document.createElement("h2");
  h2.textContent = item?.title ?? "Election";
  const meta = document.createElement("p");
  meta.className = "receipt-meta";
  meta.textContent = item?.meta ?? `Closed · ${total} ballots`;
  titleWrap.append(h2, meta);
  const pill = document.createElement("span");
  pill.className = "pill pill-counted";
  pill.textContent = "Published";
  head.append(titleWrap, pill);

  section.appendChild(head);

  const rows = Array.isArray(item?.candidates) ? item.candidates : [];
  if (rows.length > 0) {
    const winner = rows[0];
    const winnerCard = document.createElement("p");
    winnerCard.className = "winner-card";
    const strong = document.createElement("strong");
    strong.textContent = `Winner — ${winner?.name ?? "—"}`;
    const sub = document.createElement("span");
    sub.className = "winner-sub";
    sub.textContent = `${winner?.votes ?? 0} votes`;
    const wrap = document.createElement("span");
    wrap.append(strong, sub);
    winnerCard.textContent = "";
    winnerCard.append(wrap);

    const bars = document.createElement("ul");
    bars.className = "bars";
    for (const row of rows) {
      const li = document.createElement("li");
      const barRow = document.createElement("div");
      barRow.className = "bar-row";
      const name = document.createElement("span");
      name.textContent = row?.name ?? "—";
      const count = document.createElement("span");
      count.textContent = `${row?.votes ?? 0}`;
      barRow.append(name, count);
      const bar = document.createElement("div");
      bar.className = "bar";
      const fill = document.createElement("span");
      fill.dataset.votes = String(row?.votes ?? 0);
      fill.dataset.total = String(total);
      bar.appendChild(fill);
      li.append(barRow, bar);
      bars.appendChild(li);
    }
    section.append(winnerCard, bars);
  }

  const note = document.createElement("p");
  note.className = "certified-note";
  note.textContent = "Certified from the tamper-evident record. Individual choices are never shown.";
  section.appendChild(note);
  return section;
}

// API-first: append published results only when the backend answers.
// Expected: an array, or { results: [...] }. Anything else keeps demo HTML.
try {
  const data = await listResults();
  const items = Array.isArray(data) ? data : data?.results;
  const page = document.querySelector(".page");
  if (Array.isArray(items) && items.length > 0 && page) {
    for (const item of items) page.appendChild(resultSection(item));
    paintBars(page);
    refreshIcons();
  }
} catch {
  // status 0 (backend missing/offline): static demo HTML remains as preview.
}
