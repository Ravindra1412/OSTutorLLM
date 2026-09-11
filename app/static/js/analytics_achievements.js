/* =====================================================================
   OSTutorLLM — analytics_achievements.js (Part 3.9)
   Drives the Achievements page: level/XP, streak, daily/weekly goal
   bars, the earned-badges grid, and the (honest, unavailable)
   certificate placeholder.
   ===================================================================== */

(function () {
  "use strict";

  const loading = document.getElementById("achievements-loading");
  const content = document.getElementById("achievements-content");
  if (!loading || !content) return;

  function tierClass(tier) {
    return { bronze: "badge-bronze", silver: "badge-silver", gold: "badge-gold" }[tier] || "badge-locked";
  }

  function renderBadges(badges) {
    const grid = document.getElementById("badges-grid");
    const empty = document.getElementById("badges-empty");
    grid.innerHTML = "";
    if (!badges.length) {
      empty.classList.remove("d-none");
      return;
    }
    empty.classList.add("d-none");
    badges.forEach((b) => {
      const col = document.createElement("div");
      col.className = "col-md-4 col-6";
      col.innerHTML = `
        <div class="card h-100"><div class="card-body">
          <span class="badge-tier ${tierClass(b.tier)} mb-2 d-inline-block">${b.tier}</span>
          <h6 class="mb-1">${b.name}</h6>
          <p class="text-muted-custom small mb-1">${b.description}</p>
          <p class="text-muted-custom small mb-0">+${b.xp_reward} XP · ${new Date(b.earned_at).toLocaleDateString()}</p>
        </div></div>`;
      grid.appendChild(col);
    });
  }

  function renderGoal(prefix, goal, currentField, todayLabel) {
    document.getElementById(`${prefix}-bar`).style.width = `${goal.percent}%`;
    const current = goal[currentField];
    document.getElementById(`${prefix}-text`).textContent =
      `${Math.round(current)} / ${goal.goal_minutes} min ${todayLabel} ${goal.met ? "— goal met!" : ""}`;
  }

  async function loadAchievements() {
    const resp = await fetch("/api/analytics/achievements");
    const body = await resp.json();
    if (!resp.ok) {
      loading.innerHTML = `<p class="text-danger">${body.message || "Could not load achievements."}</p>`;
      return;
    }
    const data = body.data;

    document.getElementById("ach-level").textContent = data.level;
    document.getElementById("ach-xp").textContent = `${data.xp_total} XP`;
    document.getElementById("ach-streak").textContent = data.streak_days;
    document.getElementById("ach-badge-count").textContent = data.badges.length;

    renderGoal("daily", data.daily_goal, "today_minutes", "today");
    renderGoal("weekly", data.weekly_goal, "this_week_minutes", "this week");

    renderBadges(data.badges);

    document.getElementById("certificate-note").textContent = data.certificate.note;

    loading.classList.add("d-none");
    content.classList.remove("d-none");
  }

  loadAchievements();
})();
