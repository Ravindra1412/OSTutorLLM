(function () {
  "use strict";
  let questionCount = 0;

  function addQuestionRow() {
    questionCount += 1;
    const idx = questionCount;
    const div = document.createElement("div");
    div.className = "card mb-2";
    div.dataset.questionIndex = idx;
    div.innerHTML = `
      <div class="card-body">
        <div class="mb-2"><label class="form-label small">Question ${idx}</label><input class="form-control q-text"></div>
        <div class="row g-2">
          <div class="col-md-3"><input class="form-control q-opt" placeholder="Option A"></div>
          <div class="col-md-3"><input class="form-control q-opt" placeholder="Option B"></div>
          <div class="col-md-3"><input class="form-control q-opt" placeholder="Option C"></div>
          <div class="col-md-3"><input class="form-control q-opt" placeholder="Option D"></div>
        </div>
        <div class="mt-2"><label class="form-label small">Correct Answer (must match one option exactly)</label><input class="form-control q-correct"></div>
      </div>`;
    document.getElementById("questions-container").appendChild(div);
  }

  document.getElementById("add-question-btn").addEventListener("click", addQuestionRow);
  document.getElementById("quiz-modal").addEventListener("show.bs.modal", () => {
    document.getElementById("questions-container").innerHTML = "";
    questionCount = 0;
    addQuestionRow();
  });

  async function loadTopicsIntoSelect() {
    const resp = await fetch("/api/faculty/content/topics");
    const body = await resp.json();
    if (resp.ok) {
      document.getElementById("quiz-topic-select").innerHTML = body.data.map(t => `<option value="${t.id}">${t.name}</option>`).join("");
    }
  }

  async function loadQuizzes() {
    const resp = await fetch("/api/faculty/quizzes?mine_only=true");
    const body = await resp.json();
    if (!resp.ok) return;
    document.getElementById("quizzes-tbody").innerHTML = body.data.map(q => `
      <tr>
        <td>${q.title}</td><td>${q.topic_name}</td><td>${q.question_count}</td>
        <td>${q.is_published ? '<span class="text-success">Yes</span>' : '<span class="text-muted-custom">No</span>'}</td>
        <td>${q.attempt_count}</td>
        <td>
          <a href="/faculty/quizzes/${q.id}/results" class="btn btn-ghost btn-sm">Results</a>
          <button class="btn btn-ghost btn-sm" data-toggle-publish="${q.id}" data-published="${q.is_published}">${q.is_published ? "Unpublish" : "Publish"}</button>
          <button class="btn btn-ghost btn-sm text-danger" data-delete-quiz="${q.id}">Delete</button>
        </td>
      </tr>`).join("");

    document.querySelectorAll("[data-toggle-publish]").forEach(btn => btn.addEventListener("click", async () => {
      const nowPublished = btn.dataset.published !== "true";
      await fetch(`/api/faculty/quizzes/${btn.dataset.togglePublish}`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_published: nowPublished }),
      });
      loadQuizzes();
    }));
    document.querySelectorAll("[data-delete-quiz]").forEach(btn => btn.addEventListener("click", async () => {
      if (!confirm("Delete this quiz?")) return;
      await fetch(`/api/faculty/quizzes/${btn.dataset.deleteQuiz}`, { method: "DELETE" });
      loadQuizzes();
    }));
  }

  document.getElementById("save-quiz-btn").addEventListener("click", async () => {
    const questions = [...document.querySelectorAll("#questions-container .card")].map(card => {
      const opts = [...card.querySelectorAll(".q-opt")].map(i => i.value).filter(Boolean);
      return {
        question_text: card.querySelector(".q-text").value,
        question_type: "mcq",
        options: opts,
        correct_answer: card.querySelector(".q-correct").value,
      };
    });
    const payload = {
      topic_id: parseInt(document.getElementById("quiz-topic-select").value, 10),
      title: document.getElementById("quiz-title").value,
      difficulty_level: parseInt(document.getElementById("quiz-difficulty").value, 10),
      time_limit_seconds: document.getElementById("quiz-time-limit").value ? parseInt(document.getElementById("quiz-time-limit").value, 10) : null,
      is_published: document.getElementById("quiz-publish").checked,
      questions,
    };
    const resp = await fetch("/api/faculty/quizzes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (resp.ok) {
      bootstrap.Modal.getInstance(document.getElementById("quiz-modal")).hide();
      loadQuizzes();
    } else {
      const b = await resp.json();
      alert(b.message);
    }
  });

  loadTopicsIntoSelect();
  loadQuizzes();
})();
