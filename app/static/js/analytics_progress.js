/* =====================================================================
   OSTutorLLM — analytics_progress.js (Part 3.9)
   Drives the Progress page. Chart.js was chosen for Section 10's
   charting requirement because it is free, has no build step (a
   single CDN <script> tag, consistent with how Bootstrap/Bootstrap
   Icons are already loaded in public_base.html), and its canvas-based
   rendering is lightweight enough for a student-project deployment —
   fitting Part 3's "prefer free, low-cost, low-infrastructure
   solutions" requirement without pulling in a build pipeline (Vega,
   D3) that this server-rendered-template project has no tooling for.
   ===================================================================== */

(function () {
  "use strict";

  const loading = document.getElementById("progress-loading");
  const content = document.getElementById("progress-content");
  if (!loading || !content) return;

  const CHART_COLORS = {
    accent: "#FFB454",
    cyan: "#3FD0E0",
    danger: "#F17171",
    grid: "rgba(255,255,255,0.08)",
    text: "#7C8896",
  };

  function baseChartOptions(extra) {
    return Object.assign(
      {
        responsive: true,
        plugins: { legend: { labels: { color: CHART_COLORS.text } } },
        scales: {
          x: { ticks: { color: CHART_COLORS.text }, grid: { color: CHART_COLORS.grid } },
          y: { ticks: { color: CHART_COLORS.text }, grid: { color: CHART_COLORS.grid } },
        },
      },
      extra || {}
    );
  }

  function renderTopicMasteryChart(topicPerf) {
    new Chart(document.getElementById("topic-mastery-chart"), {
      type: "bar",
      data: {
        labels: topicPerf.map((t) => t.topic_name),
        datasets: [{ label: "Mastery %", data: topicPerf.map((t) => t.mastery_score), backgroundColor: CHART_COLORS.accent }],
      },
      options: baseChartOptions({ scales: { y: { beginAtZero: true, max: 100, ticks: { color: CHART_COLORS.text }, grid: { color: CHART_COLORS.grid } }, x: { ticks: { color: CHART_COLORS.text }, grid: { display: false } } } }),
    });
  }

  function renderDailyActivityChart(dailyBreakdown) {
    const labels = Object.keys(dailyBreakdown).sort();
    const values = labels.map((k) => dailyBreakdown[k]);
    new Chart(document.getElementById("daily-activity-chart"), {
      type: "line",
      data: { labels, datasets: [{ label: "Minutes", data: values, borderColor: CHART_COLORS.cyan, backgroundColor: "rgba(63,208,224,0.15)", fill: true, tension: 0.3 }] },
      options: baseChartOptions(),
    });
  }

  function renderQuizPerformanceChart(quizScores) {
    new Chart(document.getElementById("quiz-performance-chart"), {
      type: "line",
      data: {
        labels: quizScores.map((q) => new Date(q.taken_at).toLocaleDateString()),
        datasets: [{ label: "Score %", data: quizScores.map((q) => q.score), borderColor: CHART_COLORS.accent, backgroundColor: "rgba(255,180,84,0.15)", fill: true, tension: 0.3 }],
      },
      options: baseChartOptions({ scales: { y: { beginAtZero: true, max: 100, ticks: { color: CHART_COLORS.text }, grid: { color: CHART_COLORS.grid } }, x: { ticks: { color: CHART_COLORS.text }, grid: { display: false } } } }),
    });
  }

  function renderStrengthWeakness(topicPerf, weakTopics) {
    const container = document.getElementById("strength-weakness-list");
    container.innerHTML = "";
    const weakNames = new Set(weakTopics.map((w) => w.topic_name));
    const sorted = [...topicPerf].sort((a, b) => b.mastery_score - a.mastery_score);

    sorted.forEach((t) => {
      const isWeak = weakNames.has(t.topic_name) || t.mastery_score < 60;
      const el = document.createElement("div");
      el.className = "d-flex justify-content-between align-items-center p-2 rounded-lg";
      el.style.border = "1px solid var(--border-subtle)";
      el.innerHTML = `
        <span class="small">${t.topic_name}</span>
        <span class="small fw-bold" style="color:${isWeak ? CHART_COLORS.danger : "#5FD892"}">${t.mastery_score.toFixed(0)}%</span>`;
      container.appendChild(el);
    });
    if (!sorted.length) {
      container.innerHTML = '<p class="text-muted-custom small mb-0">No tracked topics yet.</p>';
    }
  }

  function renderCompletedTopics(list) {
    const container = document.getElementById("completed-topics-list");
    const empty = document.getElementById("completed-topics-empty");
    container.innerHTML = "";
    if (!list.length) {
      empty.classList.remove("d-none");
      return;
    }
    empty.classList.add("d-none");
    list.forEach((t) => {
      const span = document.createElement("span");
      span.className = "badge-tier badge-gold";
      span.textContent = `${t.topic_name} — ${t.mastery_score.toFixed(0)}%`;
      container.appendChild(span);
    });
  }

  async function loadProgress() {
    const [summaryResp, analyticsResp, weakResp] = await Promise.all([
      fetch("/api/progress/summary"),
      fetch("/api/analytics"),
      fetch("/api/analytics/weak-topics"),
    ]);
    const summary = await summaryResp.json();
    const analytics = await analyticsResp.json();
    const weak = await weakResp.json();

    if (!summaryResp.ok || !analyticsResp.ok) {
      loading.innerHTML = '<p class="text-danger">Could not load progress data.</p>';
      return;
    }

    renderTopicMasteryChart(analytics.data.topic_wise_performance);
    renderDailyActivityChart(summary.data.time_spent.daily_breakdown);
    renderQuizPerformanceChart(summary.data.quiz_scores);
    renderStrengthWeakness(analytics.data.topic_wise_performance, weak.data);
    renderCompletedTopics(summary.data.completed_topics);

    loading.classList.add("d-none");
    content.classList.remove("d-none");
  }

  loadProgress();
})();
