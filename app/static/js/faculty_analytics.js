(function () {
  "use strict";

  function renderTopicList(container, topics, key) {
    container.innerHTML = topics.length
      ? topics.map(t => `<div class="d-flex justify-content-between small mb-1"><span>${t.topic_name}</span><span class="text-accent">${t[key].toFixed(1)}%</span></div>`).join("")
      : '<p class="text-muted-custom small mb-0">None detected.</p>';
  }

  async function loadClassAnalytics() {
    const resp = await fetch("/api/faculty/analytics/class");
    const body = await resp.json();
    if (!resp.ok) return;
    const d = body.data;

    document.getElementById("stat-quiz-avg").textContent = d.quiz_statistics.average != null ? d.quiz_statistics.average.toFixed(1) + "%" : "—";
    document.getElementById("stat-accuracy").textContent = d.accuracy != null ? d.accuracy.toFixed(1) + "%" : "—";
    document.getElementById("stat-cr-score").textContent = d.code_review_statistics.average_score != null ? d.code_review_statistics.average_score.toFixed(1) : "—";
    document.getElementById("stat-hints").textContent = d.code_review_statistics.average_hints_used != null ? d.code_review_statistics.average_hints_used.toFixed(1) : "—";

    renderTopicList(document.getElementById("weak-topics"), d.weak_topics, "average_mastery");
    renderTopicList(document.getElementById("strong-topics"), d.strong_topics, "average_mastery");

    new Chart(document.getElementById("topic-chart"), {
      type: "bar",
      data: { labels: d.topic_wise_performance.map(t => t.topic_name), datasets: [{ label: "Avg Mastery %", data: d.topic_wise_performance.map(t => t.average_mastery), backgroundColor: "#FFB454" }] },
      options: { scales: { y: { beginAtZero: true, max: 100 } } },
    });
  }

  async function loadCodeReviewMonitoring() {
    const resp = await fetch("/api/faculty/analytics/code-review");
    const body = await resp.json();
    if (!resp.ok) return;
    const d = body.data;

    document.getElementById("common-mistakes").innerHTML = d.common_mistakes.length
      ? d.common_mistakes.map(m => `<div class="d-flex justify-content-between small mb-1"><span>${m.category}</span><span class="text-muted-custom">${m.occurrences}</span></div>`).join("")
      : '<p class="text-muted-custom small mb-0">No findings yet.</p>';

    new Chart(document.getElementById("trend-chart"), {
      type: "line",
      data: { labels: d.improvement_timeline.map(t => t.period), datasets: [{ label: "Avg Score", data: d.improvement_timeline.map(t => t.average_score), borderColor: "#3FD0E0", fill: false, tension: 0.3 }] },
      options: { scales: { y: { beginAtZero: true, max: 100 } } },
    });

    const tbody = document.getElementById("review-history-tbody");
    tbody.innerHTML = d.review_history.map(r => `
      <tr><td>${r.student_name}</td><td>${r.topic_name}</td><td>${r.overall_score != null ? r.overall_score.toFixed(1) : "—"}</td>
      <td>${r.hints_used}</td><td class="text-muted-custom small">${new Date(r.submitted_at).toLocaleDateString()}</td></tr>`).join("");
  }

  loadClassAnalytics();
  loadCodeReviewMonitoring();
})();
