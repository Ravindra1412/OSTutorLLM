/* =====================================================================
   OSTutorLLM — analytics_timeline.js (Part 3.9)
   Drives the Learning Timeline page: fetches GET /api/analytics/timeline
   (optionally filtered by event_type) and renders newest-first.
   ===================================================================== */

(function () {
  "use strict";

  const loading = document.getElementById("timeline-loading");
  const list = document.getElementById("timeline-list");
  const empty = document.getElementById("timeline-empty");
  const filter = document.getElementById("timeline-filter");
  if (!loading || !list) return;

  const EVENT_ICONS = {
    quiz_attempted: "bi-patch-question",
    code_review_submitted: "bi-code-slash",
    tutor_session: "bi-chat-dots",
    achievement_earned: "bi-award",
    lesson_completed: "bi-journal-check",
  };
  const EVENT_LABELS = {
    quiz_attempted: "Quiz",
    code_review_submitted: "Code Review",
    tutor_session: "Tutor Session",
    achievement_earned: "Achievement",
    lesson_completed: "Lesson",
  };

  function render(events) {
    list.innerHTML = "";
    if (!events.length) {
      list.classList.add("d-none");
      empty.classList.remove("d-none");
      return;
    }
    empty.classList.add("d-none");
    list.classList.remove("d-none");

    events.forEach((e) => {
      const el = document.createElement("div");
      el.className = "card";
      const icon = EVENT_ICONS[e.event_type] || "bi-dot";
      const label = EVENT_LABELS[e.event_type] || e.event_type;
      const scoreBadge = e.score != null ? `<span class="small text-accent">${e.score.toFixed(0)}%</span>` : "";
      const xpBadge = e.xp_earned ? `<span class="small text-muted-custom">+${e.xp_earned} XP</span>` : "";
      el.innerHTML = `
        <div class="card-body d-flex align-items-center gap-3 py-3">
          <i class="bi ${icon} fs-5 text-accent"></i>
          <div class="flex-grow-1">
            <div class="d-flex justify-content-between">
              <strong class="small">${e.title}</strong>
              ${scoreBadge}
            </div>
            <p class="text-muted-custom small mb-0">${label} · ${new Date(e.occurred_at).toLocaleString()} ${xpBadge}</p>
          </div>
        </div>`;
      list.appendChild(el);
    });
  }

  async function loadTimeline() {
    loading.classList.remove("d-none");
    list.classList.add("d-none");
    empty.classList.add("d-none");

    const params = new URLSearchParams();
    if (filter && filter.value) params.set("event_type", filter.value);
    params.set("limit", "100");

    const resp = await fetch(`/api/analytics/timeline?${params.toString()}`);
    const body = await resp.json();
    loading.classList.add("d-none");
    if (!resp.ok) {
      list.classList.remove("d-none");
      list.innerHTML = `<p class="text-danger">${body.message || "Could not load timeline."}</p>`;
      return;
    }
    render(body.data);
  }

  if (filter) filter.addEventListener("change", loadTimeline);
  loadTimeline();
})();
