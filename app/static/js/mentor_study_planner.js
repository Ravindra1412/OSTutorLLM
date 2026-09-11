(function () {
  "use strict";

  function renderWeekly(plan) {
    const container = document.getElementById("weekly-schedule");
    if (!plan || !plan.schedule) {
      container.innerHTML = '<p class="text-muted-custom small">No plan yet — click Regenerate.</p>';
      return;
    }
    container.innerHTML = plan.schedule.map(s => `
      <div class="card"><div class="card-body py-2">
        <div class="d-flex justify-content-between">
          <strong class="small">${s.day}</strong>
          <span class="small text-accent">${s.activity}</span>
        </div>
        <p class="text-muted-custom small mb-0">${s.reason}</p>
      </div></div>`).join("");
  }

  function renderMonthly(plan) {
    const container = document.getElementById("monthly-schedule");
    if (!plan || !plan.weeks) {
      container.innerHTML = '<p class="text-muted-custom small">No plan yet — click Regenerate.</p>';
      return;
    }
    container.innerHTML = plan.weeks.map(w => `
      <div class="card"><div class="card-body py-2">
        <strong class="small">Week ${w.week}: ${w.theme}</strong>
        <p class="text-muted-custom small mb-0">${w.topics.join(", ")}</p>
      </div></div>`).join("");
  }

  async function loadWeekly() {
    const resp = await fetch("/api/mentor/study-plan/weekly");
    const body = await resp.json();
    if (resp.ok) renderWeekly(body.data);
  }

  async function loadMonthly() {
    const resp = await fetch("/api/mentor/study-plan/monthly");
    const body = await resp.json();
    if (resp.ok) renderMonthly(body.data);
  }

  document.getElementById("regenerate-weekly-btn").addEventListener("click", async () => {
    const resp = await fetch("/api/mentor/study-plan/weekly/generate", { method: "POST" });
    const body = await resp.json();
    if (resp.ok) renderWeekly(body.data);
  });

  document.getElementById("regenerate-monthly-btn").addEventListener("click", async () => {
    const resp = await fetch("/api/mentor/study-plan/monthly/generate", { method: "POST" });
    const body = await resp.json();
    if (resp.ok) renderMonthly(body.data);
  });

  loadWeekly();
  loadMonthly();
})();
