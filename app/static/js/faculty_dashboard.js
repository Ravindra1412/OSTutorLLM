(function () {
  "use strict";
  const loading = document.getElementById("loading");
  const content = document.getElementById("content");

  function fmtMinutes(m) {
    return m < 60 ? `${Math.round(m)} min` : `${(m / 60).toFixed(1)} hr`;
  }

  async function load() {
    const resp = await fetch("/api/faculty/dashboard");
    const body = await resp.json();
    if (!resp.ok) {
      loading.innerHTML = `<p class="text-danger">${body.message || "Could not load dashboard."}</p>`;
      return;
    }
    const d = body.data;
    document.getElementById("stat-total").textContent = d.total_students;
    document.getElementById("stat-active").textContent = d.active_students;
    document.getElementById("stat-lessons").textContent = d.completed_lessons;
    document.getElementById("stat-quiz").textContent = d.average_quiz_score != null ? d.average_quiz_score.toFixed(1) + "%" : "—";
    document.getElementById("stat-time").textContent = fmtMinutes(d.average_learning_time_minutes);
    document.getElementById("health-db").textContent = d.system_health.database;
    document.getElementById("health-ai").textContent = d.system_health.ai_provider;
    document.getElementById("unread-count").textContent = d.unread_notifications;

    const container = document.getElementById("recent-activity");
    container.innerHTML = "";
    if (!d.recent_activity.length) {
      container.innerHTML = '<p class="text-muted-custom small mb-0">No activity yet.</p>';
    } else {
      d.recent_activity.forEach((e) => {
        const el = document.createElement("div");
        el.className = "d-flex justify-content-between small mb-2";
        el.innerHTML = `<span>${e.student_name}: ${e.title}</span><span class="text-muted-custom">${new Date(e.occurred_at).toLocaleString()}</span>`;
        container.appendChild(el);
      });
    }

    loading.classList.add("d-none");
    content.classList.remove("d-none");
  }
  load();
})();
