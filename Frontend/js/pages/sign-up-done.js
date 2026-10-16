// Done screen: recap of the new account (email + reg no only — never secrets).
// Display-only. Registration already signed the user in (token stored by
// POST /auth/register), so "Go to dashboard" works immediately; no auth
// guard here so the recap survives even if storage was cleared mid-flow.
try {
  const email = window.sessionStorage.getItem("votex-email") ?? "";
  const regno = window.sessionStorage.getItem("votex-regno") ?? "";
  if (email || regno) {
    const recap = document.querySelector("#account-recap");
    if (recap) recap.hidden = false;
    if (email) {
      const slot = document.querySelector("#recap-email");
      if (slot) slot.textContent = email;
    }
    if (regno) {
      const slot = document.querySelector("#recap-regno");
      if (slot) slot.textContent = regno;
    }
  }
} catch {
  // Storage unavailable — the page works without the recap.
}
