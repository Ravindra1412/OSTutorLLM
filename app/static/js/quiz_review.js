/* =====================================================================
   OSTutorLLM — quiz_review.js (Part 3.7)
   Renders the standalone Review Page from GET /api/quiz/<id>/review —
   always reload-safe (no sessionStorage dependency), since a review
   is something a student may revisit days later.
   ===================================================================== */

(function () {
  "use strict";

  const container = document.querySelector("[data-attempt-id]");
  if (!container) return;
  const attemptId = container.getAttribute("data-attempt-id");

  const loading = document.getElementById("review-loading");
  const content = document.getElementById("review-content");

  (async () => {
    const resp = await fetch(`/api/quiz/${attemptId}/review`);
    const body = await resp.json();
    if (!resp.ok) {
      loading.innerHTML = `<div class="alert" style="background:var(--bg-elevated);border:1px solid var(--danger);">${body.message}</div>`;
      return;
    }
    const data = body.data;
    document.getElementById("review-topic").textContent = `${data.topic} — Score: ${data.score}%`;

    content.innerHTML = data.per_question.map(pq => `
      <div class="card mb-3">
        <div class="card-body">
          <span class="badge-tier ${pq.is_correct ? "badge-gold" : ""} mb-2 d-inline-block" style="${pq.is_correct ? "" : "background:rgba(241,113,113,.15);color:var(--danger);"}">
            <i class="bi ${pq.is_correct ? "bi-check-lg" : "bi-x-lg"} me-1"></i>${pq.is_correct ? "Correct" : "Incorrect"} · ${pq.points_earned}/${pq.points_possible} pts
          </span>
          <p class="mb-1 fw-semibold">${pq.question_text}</p>
          <p class="text-muted-custom mb-2 small">Your answer: ${pq.student_answer || "(blank)"}</p>
          ${!pq.is_correct ? `<p class="text-muted-custom mb-2 small">Correct answer: ${pq.correct_answer}</p>` : ""}
          ${pq.explanation ? `<div class="feedback-item mb-0"><p class="mb-0 small text-muted-custom">${pq.explanation}</p></div>` : ""}
        </div>
      </div>
    `).join("");

    loading.classList.add("d-none");
    content.classList.remove("d-none");
  })();
})();
