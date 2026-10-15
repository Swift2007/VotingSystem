// Lucide icons are loaded from the official external CDN in index.html.
// This helper only refreshes icons after dynamic HTML injection.
export function refreshIcons() {
  if (window.lucide && typeof window.lucide.createIcons === "function") {
    window.lucide.createIcons();
  }
}
