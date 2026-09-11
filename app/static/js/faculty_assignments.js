(function () {
  "use strict";
  let submissionsModal;
  document.addEventListener("DOMContentLoaded", () => {
    submissionsModal = new bootstrap.Modal(document.getElementById("submissions-modal"));
  });

  async function loadTopicsIntoSelect() {
    const resp = await fetch("/api/faculty/content/topics");
    const body = await resp.json();
    if (resp.ok) {
      document.getElementById("a-topic").innerHTML = body.data.map(t => `<option value="${t.id}">${t.name}</option>`).join("");
    }
  }

  async function loadAssignments() {
    const resp = await fetch("/api/faculty/assignments");
    const body = await resp.json();
    if (!resp.ok) return;
    const list = document.getElementById("assignments-list");
    list.innerHTML = body.data.length
      ? body.data.map(a => `
        <div class="card card-elevated mb-2"><div class="card-body">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <strong>${a.title}</strong> <span class="text-muted-custom small">(${a.topic_name})</span>
              <p class="small mb-0">Due: ${new Date(a.due_at).toLocaleString()} · ${a.is_published ? '<span class="text-success">Published</span>' : '<span class="text-muted-custom">Draft</span>'} · ${a.submission_count} submission(s)</p>
            </div>
            <div class="d-flex gap-1">
              <button class="btn btn-ghost btn-sm" data-view-submissions="${a.id}">Submissions</button>
              <button class="btn btn-ghost btn-sm" data-remind="${a.id}">Remind</button>
              <button class="btn btn-ghost btn-sm text-danger" data-delete-assignment="${a.id}">Delete</button>
            </div>
          </div>
        </div></div>`).join("")
      : '<p class="text-muted-custom small">No assignments yet.</p>';

    list.querySelectorAll("[data-view-submissions]").forEach(btn => btn.addEventListener("click", () => viewSubmissions(btn.dataset.viewSubmissions)));
    list.querySelectorAll("[data-remind]").forEach(btn => btn.addEventListener("click", async () => {
      const resp = await fetch(`/api/faculty/assignments/${btn.dataset.remind}/remind`, { method: "POST" });
      const b = await resp.json();
      alert(b.message + (b.data ? ` (${b.data.reminded_count} students)` : ""));
    }));
    list.querySelectorAll("[data-delete-assignment]").forEach(btn => btn.addEventListener("click", async () => {
      if (!confirm("Delete this assignment?")) return;
      await fetch(`/api/faculty/assignments/${btn.dataset.deleteAssignment}`, { method: "DELETE" });
      loadAssignments();
    }));
  }

  async function viewSubmissions(assignmentId) {
    const resp = await fetch(`/api/faculty/assignments/${assignmentId}/submissions`);
    const body = await resp.json();
    if (!resp.ok) return;
    const d = body.data;
    const container = document.getElementById("submissions-body");
    container.innerHTML = d.submissions.length
      ? d.submissions.map(s => `
        <div class="card mb-2"><div class="card-body">
          <div class="d-flex justify-content-between">
            <strong class="small">${s.student_name}</strong>
            <span class="small ${s.is_late ? "text-danger" : "text-muted-custom"}">${s.is_late ? "Late" : "On time"} · ${new Date(s.submitted_at).toLocaleString()}</span>
          </div>
          <div class="d-flex gap-2 mt-2 align-items-center">
            <input type="number" class="form-control form-control-sm" style="width:100px" placeholder="Score" value="${s.score != null ? s.score : ""}" data-score-for="${s.id}">
            <button class="btn btn-outline-accent btn-sm" data-grade="${s.id}">Save Grade</button>
          </div>
        </div></div>`).join("")
      : '<p class="text-muted-custom small">No submissions yet.</p>';

    container.querySelectorAll("[data-grade]").forEach(btn => btn.addEventListener("click", async () => {
      const scoreInput = container.querySelector(`[data-score-for="${btn.dataset.grade}"]`);
      await fetch(`/api/faculty/assignments/submissions/${btn.dataset.grade}/grade`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ score: parseFloat(scoreInput.value) }),
      });
      viewSubmissions(assignmentId);
    }));
    submissionsModal.show();
  }

  document.getElementById("save-assignment-btn").addEventListener("click", async () => {
    const payload = {
      title: document.getElementById("a-title").value,
      topic_id: parseInt(document.getElementById("a-topic").value, 10),
      description: document.getElementById("a-description").value,
      due_at: document.getElementById("a-due").value,
      max_score: parseFloat(document.getElementById("a-max-score").value),
      allow_late_submission: document.getElementById("a-allow-late").checked,
      is_published: document.getElementById("a-publish").checked,
    };
    const resp = await fetch("/api/faculty/assignments", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (resp.ok) {
      bootstrap.Modal.getInstance(document.getElementById("assignment-modal")).hide();
      loadAssignments();
    } else {
      const b = await resp.json();
      alert(b.message);
    }
  });

  loadTopicsIntoSelect();
  loadAssignments();
})();
