import { dashboardPreview } from "./components/dashboard-preview.js";
import { wireNavigation } from "./components/navigation.js";

export function initLandingPage() {
  const preview = document.querySelector("#dashboard-preview");
  if (preview) preview.innerHTML = dashboardPreview();

  wireNavigation();
}
