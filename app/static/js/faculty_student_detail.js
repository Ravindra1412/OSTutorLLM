(function () {
  "use strict";
  const studentId = document.querySelector("[data-student-id]").dataset.studentId;

  function fmtMinutes(m) {
    return m < 60 ? `${Math.round(m)} min` : `${(m / 60).toFixed(1)} hr`;
  }

  async function load() {
    const resp = await fetch(`/api/faculty/students/${studentId}`);
    const body = await resp.json();
    if (!resp.ok) {
      document.getElementById("student-name").textContent = "Student not found";
      return;
    }
    const d = body.data;
    document.getElementById("student-name").textContent = d.profile.name;
    document.getElementById("stat-overall").textContent =
      d.performance_scores.overall_learning_score != null ? d.performance_scores.overall_learning_score.toFixed(1) : "—";
    document.getElementById("stat-level").textContent = `${d.achievements.level} / ${d.achievements.xp_total} XP`;
    document.getElementById("stat-topics").textContent = d.progress.tracked_topics.length;
    document.getElementById("stat-time").textContent = fmtMinutes(d.progress.time_spent.total_minutes);

    const quizEl = document.getElementById("quiz-history");
    quizEl.innerHTML = d.quiz_history.length
      ? d.quiz_history.map(q => `<div class="d-flex justify-content-between small mb-1"><span>${q.topic_name}</span><span class="text-accent">${q.score.toFixed(1)}%</span></div>`).join("")
      : '<p class="text-muted-custom small mb-0">No quiz attempts yet.</p>';

    const crEl = document.getElementById("code-review-history");
    crEl.innerHTML = d.code_review_history.length
      ? d.code_review_history.map(c => `<div class="d-flex justify-content-between small mb-1"><span>${c.topic_name}</span><span class="text-accent">${c.overall_score != null ? c.overall_score.toFixed(1) : "—"}</span></div>`).join("")
      : '<p class="text-muted-custom small mb-0">No code reviews yet.</p>';

    const tsEl = document.getElementById("tutor-sessions");
    tsEl.innerHTML = d.tutor_sessions.length
      ? d.tutor_sessions.map(t => `<div class="small mb-1">${t.topic_name} — ${new Date(t.started_at).toLocaleDateString()}</div>`).join("")
      : '<p class="text-muted-custom small mb-0">No tutor sessions yet.</p>';

    const achEl = document.getElementById("achievements-list");
    achEl.innerHTML = d.achievements.badges.length
      ? d.achievements.badges.map(b => `<span class="badge-tier badge-${b.tier} me-1 mb-1 d-inline-block">${b.name}</span>`).join("")
      : '<p class="text-muted-custom small mb-0">No badges earned yet.</p>';
  }

  document.getElementById("send-alert-btn").addEventListener("click", async () => {
    const message = document.getElementById("alert-message").value.trim();
    if (!message) return;
    const resp = await fetch(`/api/faculty/students/${studentId}/alert`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }),
    });
    if (resp.ok) {
      document.getElementById("alert-sent-msg").classList.remove("d-none");
      document.getElementById("alert-message").value = "";
    }
  });

  load();
})();
