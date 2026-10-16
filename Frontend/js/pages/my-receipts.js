// My Receipts: GET /receipts/mine via services/, rendered into the same
// .receipt-list cards as the static demo HTML. When the backend is missing
// (network error), the static demo cards stay untouched so the page still
// previews. Copy + verify handoff keep working for both paths.
import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";
import { listMyReceipts } from "../../services/receipt.service.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

/** Copy buttons: clipboard write with visible confirmation. */
function wireCopyButtons(scope = document) {
  scope.querySelectorAll(".copy-btn").forEach((button) => {
    if (button instanceof HTMLElement && button.dataset.wired) return;
    if (button instanceof HTMLElement) button.dataset.wired = "1";
    button.addEventListener("click", async () => {
      const text = button.dataset.copy ?? "";
      const label = button.querySelector("span");
      const original = label?.textContent ?? "Copy";
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        // Clipboard unavailable — still confirm the code visibly.
      }
      if (label) label.textContent = "Copied ✓";
      window.setTimeout(() => {
        if (label) label.textContent = original;
      }, 1500);
    });
  });
}

/** Verify links: pass the code via sessionStorage (never in the URL). */
function wireVerifyLinks(scope = document) {
  scope.querySelectorAll(".verify-link").forEach((link) => {
    if (link instanceof HTMLElement && link.dataset.wired) return;
    if (link instanceof HTMLElement) link.dataset.wired = "1";
    link.addEventListener("click", () => {
      try {
        window.sessionStorage.setItem("votex-verify-code", link.dataset.code ?? "");
      } catch {
        // Non-essential convenience only.
      }
    });
  });
}

wireCopyButtons();
wireVerifyLinks();

/** Build one .receipt-card from an API item (textContent only — codes are untrusted). */
function receiptCard(item) {
  const code = item?.code ?? item?.receipt_code ?? "";
  const title = item?.election ?? item?.election_title ?? item?.title ?? "Election";
  const meta = item?.meta ?? item?.voted_at ?? item?.created_at ?? "";
  const counted = (item?.status ?? "counted").toLowerCase() !== "recorded";

  const li = document.createElement("li");
  li.className = "receipt-card";

  const top = document.createElement("div");
  top.className = "receipt-top";
  const head = document.createElement("div");
  const h2 = document.createElement("h2");
  h2.textContent = title;
  const metaEl = document.createElement("p");
  metaEl.className = "receipt-meta";
  metaEl.textContent = meta;
  head.append(h2, metaEl);

  const pill = document.createElement("span");
  pill.className = `pill ${counted ? "pill-counted" : "pill-recorded"}`;
  pill.textContent = counted ? "Counted" : "Recorded";
  top.append(head, pill);

  const row = document.createElement("div");
  row.className = "code-row";
  const codeEl = document.createElement("code");
  codeEl.textContent = code;
  const copy = document.createElement("button");
  copy.className = "copy-btn";
  copy.type = "button";
  copy.dataset.copy = code;
  copy.textContent = "Copy";
  row.append(codeEl, copy);

  const verify = document.createElement("a");
  verify.className = "inline-link verify-link";
  verify.href = "./verify-receipt.html";
  verify.dataset.code = code;
  verify.textContent = "Verify this receipt →";

  li.append(top, row, verify);
  return li;
}

// API-first: replace demo cards only when the backend answers.
// Expected: an array, or { receipts: [...] }. Any other shape keeps demo HTML.
try {
  const data = await listMyReceipts();
  const items = Array.isArray(data) ? data : data?.receipts;
  const list = document.querySelector(".receipt-list");
  if (Array.isArray(items) && items.length > 0 && list) {
    list.textContent = "";
    for (const item of items) list.appendChild(receiptCard(item));
    wireCopyButtons(list);
    wireVerifyLinks(list);
    refreshIcons();
  }
  // Empty array = genuinely no receipts yet: keep demo cards as preview.
} catch {
  // status 0 (backend missing/offline): static demo HTML remains as preview.
}
