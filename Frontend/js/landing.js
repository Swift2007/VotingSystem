import { dashboardPreview } from "./components/dashboard-preview.js";
import { wireNavigation } from "./components/navigation.js";
import { refreshIcons } from "./components/icons.js";
import { initReveal } from "./components/reveal.js";

export function initLandingPage() {
  const preview = document.querySelector("#dashboard-preview");
  if (preview) preview.innerHTML = dashboardPreview();

  wireNavigation();
  refreshIcons();
  initReveal();
  window.addEventListener("load", refreshIcons, { once: true });
}
