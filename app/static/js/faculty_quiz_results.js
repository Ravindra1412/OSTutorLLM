(function () {
  "use strict";
  const quizId = document.querySelector("[data-quiz-id]").dataset.quizId;

  async function load() {
    const resp = await fetch(`/api/faculty/quizzes/${quizId}/results`);
    const body = await resp.json();
    if (!resp.ok) {
      document.getElementById("quiz-title").textContent = "Quiz not found";
      return;
    }
    const d = body.data;
    document.getElementById("quiz-title").textContent = `${d.quiz_title} — ${d.topic_name}`;
    document.getElementById("empty-msg").style.display = d.results.length ? "none" : "block";
    document.getElementById("results-tbody").innerHTML = d.results.map(r => `
      <tr><td>${r.student_name}</td><td class="text-muted-custom">${r.student_email}</td>
      <td>${r.score_percent != null ? r.score_percent.toFixed(1) + "%" : "—"}</td>
      <td class="text-muted-custom small">${r.completed_at ? new Date(r.completed_at).toLocaleString() : "—"}</td></tr>`).join("");
  }
  load();
})();
