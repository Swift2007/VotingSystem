export function dashboardPreview() {
  return `
    <div class="dashboard" role="img" aria-label="Dashboard preview showing an open election, upcoming elections, and a vote receipt">
      <div class="window-bar" aria-hidden="true">
        <i class="window-dot"></i><i class="window-dot"></i><i class="window-dot"></i>
      </div>
      <div class="dashboard-body">
        <aside class="dash-sidebar" aria-hidden="true">
          <div class="dash-side-item active"><span class="side-icon">◈</span>Dashboard</div>
          <div class="dash-side-item"><span class="side-icon">▭</span>Elections</div>
          <div class="dash-side-item"><span class="side-icon">▤</span>My Receipts</div>
          <div class="dash-side-item"><span class="side-icon">◇</span>Verify</div>
          <div class="dash-side-item"><span class="side-icon">▥</span>Results</div>
        </aside>
        <div class="dash-main">
          <p class="welcome">Welcome back,<strong>Amara Okafor</strong></p>
          <div class="stats">
            <div class="stat"><span class="stat-label">Open</span><span class="stat-value">1</span></div>
            <div class="stat"><span class="stat-label">Votes cast</span><span class="stat-value">4</span></div>
            <div class="stat"><span class="stat-label">Upcoming</span><span class="stat-value">2</span></div>
          </div>
          <div class="election-list">
            <div class="election-row">
              <div class="election-text">
                <span class="election-title">Student Council 2026</span>
                <span class="election-date">Closes today, 18:00</span>
              </div>
              <span class="status status-open">Open</span>
              <span class="vote-now">Vote now</span>
            </div>
            <div class="election-row">
              <div class="election-text">
                <span class="election-title">Faculty Rep — Science</span>
                <span class="election-date">Opens 12 May</span>
              </div>
              <span class="status status-upcoming">Upcoming</span>
            </div>
            <div class="election-row">
              <div class="election-text">
                <span class="election-title">Sports Captain</span>
                <span class="election-date">Closed 28 Apr</span>
              </div>
              <span class="status status-closed">Closed</span>
            </div>
          </div>
          <div class="latest-receipt"><span>▤ &nbsp;Latest receipt</span><span class="receipt-code">VC · 7QK4 · 93X2</span></div>
        </div>
      </div>
    </div>
  `.trim();
}
