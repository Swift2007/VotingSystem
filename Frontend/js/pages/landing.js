import { dashboardPreview } from "../components/landing/dashboard-preview.js";
import { wireNavigation } from "../components/navigation.js";
import { refreshIcons } from "../shared/icons.js";
import { initReveal } from "../components/landing/reveal.js";

export function initLandingPage() {
  const preview = document.querySelector("#dashboard-preview");
  if (preview) preview.innerHTML = dashboardPreview();

  wireNavigation();
  refreshIcons();
  initReveal();
  if (document.readyState !== "complete") {
    window.addEventListener("load", refreshIcons, { once: true });
  }
}

initLandingPage();
