(function () {
  "use strict";
  const loading = document.getElementById("loading");
  const content = document.getElementById("content");

  function renderHealthFactors(factors, missing) {
    const container = document.getElementById("health-factors");
    container.innerHTML = "";
    Object.entries(factors).forEach(([key, value]) => {
      const label = key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      const display = value != null ? value.toFixed(0) : "no data";
      container.innerHTML += `
        <div class="d-flex justify-content-between small mb-1">
          <span>${label}</span>
          <span class="${value == null ? 'text-muted-custom' : 'text-accent'}">${display}</span>
        </div>`;
    });
  }

  function renderList(elementId, items, emptyText) {
    const el = document.getElementById(elementId);
    el.innerHTML = items.length ? items.map(t => `<div class="small mb-1">• ${t}</div>`).join("") : `<p class="text-muted-custom small mb-0">${emptyText}</p>`;
  }

  function renderInsights(insights) {
    const el = document.getElementById("insights-list");
    el.innerHTML = insights.map(i => `
      <div class="mb-2 pb-2" style="border-bottom:1px solid var(--border-subtle);">
        <p class="mb-0">${i.text}</p>
        <p class="text-muted-custom small mb-0">${i.evidence || ""}</p>
      </div>`).join("");
  }

  function renderTodaysPlan(plan) {
    const el = document.getElementById("todays-plan");
    if (!plan || !plan.focus) {
      el.innerHTML = '<p class="text-muted-custom small mb-0">No plan generated yet.</p>';
      return;
    }
    el.innerHTML = `<h6>${plan.focus.activity}</h6><p class="text-muted-custom small mb-0">${plan.focus.reason}</p>`;
  }

  function renderRecommendations(recs) {
    const el = document.getElementById("recommendations-list");
    el.innerHTML = recs.length
      ? recs.slice(0, 4).map(r => `<div class="mb-2"><strong class="small">${r.title}</strong><p class="text-muted-custom small mb-0">${r.reason}</p></div>`).join("")
      : '<p class="text-muted-custom small mb-0">No recommendations yet.</p>';
  }

  function renderOverview(d) {
    document.getElementById("health-score").textContent = d.learning_health.health_score.toFixed(0);
    document.getElementById("health-status-badge").textContent = d.learning_health.status;
    document.getElementById("confidence-score").textContent = d.confidence.overall_confidence != null ? d.confidence.overall_confidence.toFixed(0) : "—";
    document.getElementById("confidence-subtitle").textContent = `Command: ${d.confidence.command_confidence != null ? d.confidence.command_confidence.toFixed(0) : "—"} · Programming: ${d.confidence.programming_confidence != null ? d.confidence.programming_confidence.toFixed(0) : "—"}`;
    document.getElementById("learning-style").textContent = d.student_profile.learning_style.label;
    document.getElementById("learning-style-basis").textContent = d.student_profile.learning_style.basis || "";

    renderHealthFactors(d.learning_health.factors, d.learning_health.factors_missing_data);
    renderList("confidence-improved", d.confidence.why.what_improved, "Nothing new yet.");
    renderList("confidence-needs-work", d.confidence.why.what_needs_work, "Nothing flagged right now.");
    renderInsights(d.insights);
    renderTodaysPlan(d.todays_plan);
    renderRecommendations(d.recommendations);

    loading.classList.add("d-none");
    content.classList.remove("d-none");
  }

  async function load(refresh) {
    const url = refresh ? "/api/mentor/refresh" : "/api/mentor/overview";
    const resp = await fetch(url, { method: refresh ? "POST" : "GET" });
    const body = await resp.json();
    if (resp.ok) renderOverview(body.data);
  }

  document.getElementById("refresh-mentor-btn").addEventListener("click", () => {
    loading.classList.remove("d-none");
    content.classList.add("d-none");
    load(true);
  });

  async function loadHistory() {
    const resp = await fetch("/api/mentor/assistant/history");
    const body = await resp.json();
    if (!resp.ok) return;
    document.getElementById("ask-history").innerHTML = body.data.map(h => `
      <div class="small mb-2"><strong>Q:</strong> ${h.question}<br><strong>A:</strong> ${h.answer}</div>
    `).join("");
  }

  document.getElementById("ask-btn").addEventListener("click", async () => {
    const input = document.getElementById("ask-input");
    if (!input.value.trim()) return;
    const resp = await fetch("/api/mentor/assistant/ask", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: input.value.trim() }),
    });
    const body = await resp.json();
    if (resp.ok) {
      const answerBox = document.getElementById("ask-answer");
      answerBox.textContent = body.data.answer;
      answerBox.classList.remove("d-none");
      input.value = "";
      loadHistory();
    }
  });

  load(false);
  loadHistory();
})();
