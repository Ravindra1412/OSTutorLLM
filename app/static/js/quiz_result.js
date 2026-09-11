/* =====================================================================
   OSTutorLLM — quiz_result.js (Part 3.7)
   Renders the Result Page. Prefers the sessionStorage handoff from
   quiz_engine.js's submit handler (includes the ephemeral AI mistake
   analysis + freshly-earned badges); falls back to GET
   /api/quiz/<id>/review (reload-safe, persisted data only) if the
   page was reloaded or revisited later and sessionStorage is empty —
   an honest degrade rather than a broken page.
   ===================================================================== */

(function () {
  "use strict";

  const container = document.querySelector("[data-attempt-id]");
  if (!container) return;
  const attemptId = container.getAttribute("data-attempt-id");

  const loading = document.getElementById("result-loading");
  const content = document.getElementById("result-content");

  function scoreBand(score) {
    if (score >= 80) return "mastery-band-high";
    if (score >= 50) return "mastery-band-mid";
    return "mastery-band-low";
  }

  function renderFromSubmitPayload(data) {
    document.getElementById("score-display").textContent = `${data.score_percent}%`;
    document.getElementById("score-display").className = `fs-1 fw-bold font-display ${scoreBand(data.score_percent)}`;
    document.getElementById("score-fraction-display").textContent =
      `${data.summary.correct_count} / ${data.summary.total_questions} correct`;
    document.getElementById("mistake-analysis").textContent = data.feedback.mistake_analysis;
    document.getElementById("review-link").href = `/quiz/attempt/${attemptId}/review`;

    if (data.newly_earned_badges && data.newly_earned_badges.length) {
      document.getElementById("badges-earned").innerHTML = data.newly_earned_badges.map(name =>
        `<span class="badge-tier badge-gold me-1"><i class="bi bi-trophy me-1"></i>${name}</span>`
      ).join("");
    }

    if (data.feedback.next_topic_recommendation) {
      document.getElementById("next-topic-card").style.display = "block";
      document.getElementById("next-topic-text").textContent = data.feedback.next_topic_recommendation;
    }

    document.getElementById("question-breakdown").innerHTML = data.feedback.per_question.map(pq => `
      <div class="card mb-3">
        <div class="card-body">
          <span class="badge-tier ${pq.is_correct ? "badge-gold" : ""} mb-2 d-inline-block" style="${pq.is_correct ? "" : "background:rgba(241,113,113,.15);color:var(--danger);"}">
            <i class="bi ${pq.is_correct ? "bi-check-lg" : "bi-x-lg"} me-1"></i>${pq.is_correct ? "Correct" : "Incorrect"} · ${pq.points_earned}/${pq.points_possible} pts
          </span>
          <p class="mb-1 fw-semibold">${pq.question_text}</p>
          ${!pq.is_correct ? `<p class="text-muted-custom mb-2 small">Your answer: ${pq.student_answer || "(blank)"} · Correct: ${pq.correct_answer}</p>` : ""}
          ${pq.explanation ? `<div class="feedback-item mb-0"><p class="mb-0 small text-muted-custom">${pq.explanation}</p></div>` : ""}
        </div>
      </div>
    `).join("");
  }

  async function renderFromReviewEndpoint() {
    const resp = await fetch(`/api/quiz/${attemptId}/review`);
    const body = await resp.json();
    if (!resp.ok) {
      loading.innerHTML = `<div class="alert" style="background:var(--bg-elevated);border:1px solid var(--danger);">${body.message}</div>`;
      return;
    }
    const data = body.data;
    const correctCount = data.per_question.filter(pq => pq.is_correct).length;
    renderFromSubmitPayload({
      score_percent: data.score,
      summary: { correct_count: correctCount, total_questions: data.per_question.length },
      feedback: {
        mistake_analysis: "Revisit note: detailed AI feedback is only shown right after submitting. Here's your persisted result.",
        next_topic_recommendation: null,
        per_question: data.per_question,
      },
      newly_earned_badges: [],
    });
  }

  const cached = sessionStorage.getItem(`quiz_result_${attemptId}`);
  (async () => {
    if (cached) {
      renderFromSubmitPayload(JSON.parse(cached));
      sessionStorage.removeItem(`quiz_result_${attemptId}`);
    } else {
      await renderFromReviewEndpoint();
    }
    loading.classList.add("d-none");
    content.classList.remove("d-none");
  })();
})();
