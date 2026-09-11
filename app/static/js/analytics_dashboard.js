/* =====================================================================
   OSTutorLLM — analytics_dashboard.js (Part 3.9)
   Drives the Student Dashboard: fetches GET /api/analytics/dashboard
   and renders the overview cards, daily goal bar, weak topics,
   recommendation preview, and recent timeline preview.
   ===================================================================== */

(function () {
  "use strict";

  const loading = document.getElementById("dashboard-loading");
  const content = document.getElementById("dashboard-content");
  if (!loading || !content) return;

  const EVENT_ICONS = {
    quiz_attempted: "bi-patch-question",
    code_review_submitted: "bi-code-slash",
    tutor_session: "bi-chat-dots",
    achievement_earned: "bi-award",
    lesson_completed: "bi-journal-check",
  };

  function fmtMinutes(mins) {
    if (mins < 60) return `${Math.round(mins)} min`;
    return `${(mins / 60).toFixed(1)} hr`;
  }

  function renderWeakTopics(list) {
    const container = document.getElementById("weak-topics-list");
    const empty = document.getElementById("weak-topics-empty");
    container.innerHTML = "";
    if (!list.length) {
      empty.classList.remove("d-none");
      return;
    }
    empty.classList.add("d-none");
    list.forEach((t) => {
      const el = document.createElement("div");
      el.className = "p-2 rounded-lg border-subtle";
      el.style.border = "1px solid var(--border-subtle)";
      el.innerHTML = `
        <div class="d-flex justify-content-between">
          <strong class="small">${t.topic_name}</strong>
          <span class="small text-muted-custom">${t.mastery_score != null ? t.mastery_score.toFixed(0) + "%" : "—"}</span>
        </div>
        <p class="text-muted-custom small mb-0">${t.signals[0] || ""}</p>`;
      container.appendChild(el);
    });
  }

  function renderRecommendations(list) {
    const container = document.getElementById("dashboard-recommendations");
    const empty = document.getElementById("recommendations-empty");
    container.innerHTML = "";
    if (!list.length) {
      empty.classList.remove("d-none");
      return;
    }
    empty.classList.add("d-none");
    list.slice(0, 4).forEach((r) => {
      const el = document.createElement("div");
      el.className = "p-2 rounded-lg";
      el.style.border = "1px solid var(--border-subtle)";
      el.innerHTML = `
        <strong class="small">${r.title}</strong>
        <p class="text-muted-custom small mb-0">${r.reason}</p>`;
      container.appendChild(el);
    });
  }

  function renderTimeline(list) {
    const container = document.getElementById("dashboard-timeline");
    container.innerHTML = "";
    if (!list.length) {
      container.innerHTML = '<p class="text-muted-custom small mb-0">No activity yet — start a tutor session, quiz, or code review.</p>';
      return;
    }
    list.forEach((e) => {
      const el = document.createElement("div");
      el.className = "d-flex align-items-center gap-2";
      const icon = EVENT_ICONS[e.event_type] || "bi-dot";
      const when = new Date(e.occurred_at).toLocaleString();
      el.innerHTML = `
        <i class="bi ${icon} text-accent"></i>
        <span class="small flex-grow-1">${e.title}</span>
        <span class="small text-muted-custom">${when}</span>`;
      container.appendChild(el);
    });
  }

  function renderDashboard(data) {
    document.getElementById("stat-overall").textContent =
      data.performance_scores.overall_learning_score != null
        ? data.performance_scores.overall_learning_score.toFixed(1)
        : "—";
    document.getElementById("stat-level").textContent = data.achievements.level;
    document.getElementById("stat-xp").textContent = `${data.achievements.xp_total} XP`;
    document.getElementById("stat-streak").textContent = data.achievements.streak_days;
    document.getElementById("stat-topics").textContent = data.progress.tracked_topic_count;

    const goal = data.achievements.daily_goal;
    document.getElementById("daily-goal-bar").style.width = `${goal.percent}%`;
    document.getElementById("daily-goal-text").textContent =
      `${Math.round(goal.today_minutes)} / ${goal.goal_minutes} min ${goal.met ? "— goal met!" : ""}`;

    document.getElementById("time-today").textContent = fmtMinutes(data.progress.time_spent.today_minutes);
    document.getElementById("time-week").textContent = fmtMinutes(data.progress.time_spent.this_week_minutes);
    document.getElementById("time-month").textContent = fmtMinutes(data.progress.time_spent.this_month_minutes);

    renderWeakTopics(data.weak_topics);
    renderRecommendations(data.recommendations);
    renderTimeline(data.recent_timeline);

    loading.classList.add("d-none");
    content.classList.remove("d-none");
  }

  async function loadDashboard(refresh) {
    const url = refresh ? "/api/analytics/dashboard/refresh" : "/api/analytics/dashboard";
    const resp = await fetch(url, { method: refresh ? "POST" : "GET" });
    const body = await resp.json();
    if (!resp.ok) {
      loading.innerHTML = `<p class="text-danger">${body.message || "Could not load dashboard."}</p>`;
      return;
    }
    renderDashboard(body.data);
  }

  const refreshBtn = document.getElementById("refresh-dashboard-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      loading.classList.remove("d-none");
      content.classList.add("d-none");
      loadDashboard(true);
    });
  }

  loadDashboard(false);
})();
