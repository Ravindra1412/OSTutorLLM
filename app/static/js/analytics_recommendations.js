/* =====================================================================
   OSTutorLLM — analytics_recommendations.js (Part 3.9)
   Drives the Recommendation page: lists active (non-dismissed)
   recommendations, lets the student dismiss one, and regenerates the
   full set via POST /api/analytics/recommendations/sync.
   ===================================================================== */

(function () {
  "use strict";

  const loading = document.getElementById("recs-loading");
  const list = document.getElementById("recs-list");
  const empty = document.getElementById("recs-empty");
  const regenerateBtn = document.getElementById("regenerate-btn");
  if (!loading || !list) return;

  const TYPE_LABELS = {
    next_lesson: "New Topic",
    next_quiz: "Quiz",
    revision: "Revision",
    practice: "Practice",
    reading: "Reading",
  };
  const PRIORITY_COLORS = { 1: "#F17171", 2: "#FFB454", 3: "#7C8896" };

  function render(recs) {
    list.innerHTML = "";
    if (!recs.length) {
      list.classList.add("d-none");
      empty.classList.remove("d-none");
      return;
    }
    empty.classList.add("d-none");
    list.classList.remove("d-none");

    recs.forEach((r) => {
      const el = document.createElement("div");
      el.className = "card card-elevated";
      el.innerHTML = `
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-1">
            <span class="badge-tier" style="background:${PRIORITY_COLORS[r.priority]}22;color:${PRIORITY_COLORS[r.priority]};">
              ${TYPE_LABELS[r.rec_type] || r.rec_type}
            </span>
            <button class="btn btn-ghost btn-sm" data-dismiss-id="${r.id}"><i class="bi bi-x-lg"></i></button>
          </div>
          <h6 class="mb-1">${r.title}</h6>
          <p class="text-muted-custom small mb-0">${r.reason}</p>
        </div>`;
      list.appendChild(el);
    });

    list.querySelectorAll("[data-dismiss-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-dismiss-id");
        btn.disabled = true;
        await fetch(`/api/analytics/recommendations/${id}/dismiss`, { method: "POST" });
        loadRecommendations();
      });
    });
  }

  async function loadRecommendations() {
    loading.classList.remove("d-none");
    list.classList.add("d-none");
    empty.classList.add("d-none");

    const resp = await fetch("/api/analytics/recommendations");
    const body = await resp.json();
    loading.classList.add("d-none");
    if (!resp.ok) {
      list.classList.remove("d-none");
      list.innerHTML = `<p class="text-danger">${body.message || "Could not load recommendations."}</p>`;
      return;
    }
    render(body.data);
  }

  if (regenerateBtn) {
    regenerateBtn.addEventListener("click", async () => {
      regenerateBtn.disabled = true;
      await fetch("/api/analytics/recommendations/sync", { method: "POST" });
      regenerateBtn.disabled = false;
      loadRecommendations();
    });
  }

  loadRecommendations();
})();
