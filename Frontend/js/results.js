import { refreshIcons } from "./components/icons.js";

// Results: icons + bar widths from vote data (demo totals until the API exists).
refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

document.querySelectorAll(".bar span[data-votes]").forEach((fill) => {
  const votes = Number(fill.dataset.votes) || 0;
  const total = Number(fill.dataset.total) || 1;
  requestAnimationFrame(() => {
    fill.style.width = `${Math.min(100, (votes / total) * 100)}%`;
  });
});
