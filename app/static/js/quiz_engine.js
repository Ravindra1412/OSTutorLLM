/* =====================================================================
   OSTutorLLM — quiz_engine.js (Part 3.7)
   Drives the Question Page: fetches the started quiz, renders each
   question by type, tracks answers client-side, saves each answer to
   the server via /api/quiz/<id>/answer, runs the server-authoritative
   countdown (Section 8), and submits via /api/quiz/<id>/submit.

   Security note (Section 19): this file never receives or stores a
   correct_answer — the API response for /api/quiz/start and
   /api/quiz/<id> deliberately excludes it (see quiz_routes.py's
   _serialize_question_for_student). Grading happens entirely
   server-side on submit.
   ===================================================================== */

(function () {
  "use strict";

  const container = document.querySelector("[data-attempt-id]");
  if (!container) return;
  const attemptId = container.getAttribute("data-attempt-id");

  let questions = [];
  let current = 0;
  const answers = {};       // questionId -> raw answer value (string or array/object for complex types)
  let remainingSeconds = null;
  let timerInterval = null;
  let isPaused = false;

  const loadingState = document.getElementById("loading-state");
  const quizCard = document.getElementById("quizCard");
  const questionContainer = document.getElementById("question-container");
  const progressTrack = document.getElementById("quizProgressTrack");
  const currentLabel = document.getElementById("q-current");
  const totalLabel = document.getElementById("q-total");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const submitBtn = document.getElementById("submit-btn");
  const timerDisplay = document.getElementById("quiz-timer");
  const pauseBtn = document.getElementById("pause-btn");
  const errorBox = document.getElementById("submit-error");

  async function loadQuiz() {
    const resp = await fetch(`/api/quiz/${attemptId}`);
    const body = await resp.json();
    if (!resp.ok) {
      if (resp.status === 409 || (body.message && body.message.toLowerCase().includes("already been submitted"))) {
        window.location.href = `/quiz/attempt/${attemptId}/result`;
        return;
      }
      loadingState.innerHTML = `<p class="text-danger">${body.message || "Could not load this quiz."}</p>`;
      return;
    }

    if (body.data.is_submitted) {
      window.location.href = `/quiz/attempt/${attemptId}/result`;
      return;
    }

    questions = body.data.questions;
    remainingSeconds = body.data.remaining_seconds;

    totalLabel.textContent = questions.length;
    buildProgressTrack();
    renderQuestion(0);
    startTimerDisplay();

    loadingState.classList.add("d-none");
    quizCard.classList.remove("d-none");
  }

  function buildProgressTrack() {
    progressTrack.innerHTML = "";
    questions.forEach((_, i) => {
      const seg = document.createElement("div");
      seg.className = "quiz-progress-track__seg" + (i === 0 ? " current" : "");
      progressTrack.appendChild(seg);
    });
  }

  function updateProgressTrack() {
    const segs = progressTrack.children;
    for (let i = 0; i < segs.length; i++) {
      segs[i].classList.remove("current", "done");
      if (i < current) segs[i].classList.add("done");
      else if (i === current) segs[i].classList.add("current");
    }
  }

  function renderQuestion(index) {
    current = index;
    const q = questions[index];
    currentLabel.textContent = index + 1;
    updateProgressTrack();
    prevBtn.disabled = index === 0;
    const isLast = index === questions.length - 1;
    nextBtn.classList.toggle("d-none", isLast);
    submitBtn.classList.toggle("d-none", !isLast);

    questionContainer.innerHTML = "";
    const typeBadge = document.createElement("span");
    typeBadge.className = "badge-tier badge-bronze mb-3 d-inline-block";
    typeBadge.textContent = q.question_type_label;
    questionContainer.appendChild(typeBadge);

    const heading = document.createElement("h5");
    heading.className = "mb-4";
    heading.innerHTML = renderQuestionText(q.question_text);
    questionContainer.appendChild(heading);

    questionContainer.appendChild(buildAnswerInput(q));
  }

  function renderQuestionText(text) {
    const escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return escaped.replace(/```([\s\S]*?)```/g, "<pre class='code-block'>$1</pre>").replace(/\n/g, "<br>");
  }

  function buildAnswerInput(q) {
    const wrap = document.createElement("div");
    const existing = answers[q.id];

    switch (q.question_type) {
      case "mcq":
      case "command_prediction":
      case "output_prediction": {
        if (q.options) {
          q.options.forEach(opt => wrap.appendChild(buildChoiceButton(q, opt, existing === opt, false)));
        } else {
          wrap.appendChild(buildTextInput(q, existing));
        }
        break;
      }
      case "true_false": {
        ["true", "false"].forEach(opt => wrap.appendChild(buildChoiceButton(q, opt, existing === opt, false)));
        break;
      }
      case "multi_select": {
        const selected = existing ? JSON.parse(existing) : [];
        q.options.forEach(opt => wrap.appendChild(buildChoiceButton(q, opt, selected.includes(opt), true)));
        break;
      }
      case "fill_blank": {
        wrap.appendChild(buildTextInput(q, existing));
        break;
      }
      case "shell_programming":
      case "error_identification":
      case "scenario":
      case "case_study":
      case "viva": {
        wrap.appendChild(buildTextArea(q, existing));
        break;
      }
      case "match_the_following": {
        wrap.appendChild(buildMatchingInput(q, existing));
        break;
      }
      case "drag_and_drop": {
        wrap.appendChild(buildOrderingInput(q, existing));
        break;
      }
      default:
        wrap.appendChild(buildTextArea(q, existing));
    }
    return wrap;
  }

  function buildChoiceButton(q, optionText, isSelected, multi) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "quiz-option" + (isSelected ? " selected" : "");
    btn.innerHTML = `<i class="bi ${multi ? (isSelected ? "bi-check-square-fill" : "bi-square") : (isSelected ? "bi-check-circle-fill" : "bi-circle")} me-2"></i>${optionText}`;
    btn.addEventListener("click", () => {
      if (multi) {
        let selected = answers[q.id] ? JSON.parse(answers[q.id]) : [];
        if (selected.includes(optionText)) selected = selected.filter(o => o !== optionText);
        else selected.push(optionText);
        saveAnswer(q.id, JSON.stringify(selected));
        renderQuestion(current);
      } else {
        saveAnswer(q.id, optionText);
        renderQuestion(current);
      }
    });
    return btn;
  }

  function buildTextInput(q, existing) {
    const input = document.createElement("input");
    input.type = "text";
    input.className = "form-control";
    input.placeholder = "Type your answer...";
    input.value = existing || "";
    input.addEventListener("change", () => saveAnswer(q.id, input.value));
    return input;
  }

  function buildTextArea(q, existing) {
    const textarea = document.createElement("textarea");
    textarea.className = "form-control";
    textarea.rows = 5;
    textarea.placeholder = "Type your answer...";
    textarea.value = existing || "";
    textarea.addEventListener("change", () => saveAnswer(q.id, textarea.value));
    return textarea;
  }

  function buildMatchingInput(q, existing) {
    const wrap = document.createElement("div");
    const submitted = existing ? JSON.parse(existing) : {};
    const opts = q.options || { left: [], right: [] };

    opts.left.forEach((leftItem, i) => {
      const row = document.createElement("div");
      row.className = "d-flex align-items-center gap-2 mb-2";
      const label = document.createElement("span");
      label.style.width = "45%";
      label.textContent = leftItem;
      const select = document.createElement("select");
      select.className = "form-select";
      select.innerHTML = `<option value="">-- match --</option>` +
        opts.right.map((r, ri) => `<option value="${ri}" ${submitted[i] == ri ? "selected" : ""}>${r}</option>`).join("");
      select.addEventListener("change", () => {
        const current_map = answers[q.id] ? JSON.parse(answers[q.id]) : {};
        current_map[i] = select.value;
        saveAnswer(q.id, JSON.stringify(current_map));
      });
      row.appendChild(label);
      row.appendChild(select);
      wrap.appendChild(row);
    });
    return wrap;
  }

  function buildOrderingInput(q, existing) {
    const wrap = document.createElement("div");
    let order = existing ? JSON.parse(existing) : (q.options || []).map((_, i) => i);

    function render() {
      wrap.innerHTML = "";
      order.forEach((optIndex, pos) => {
        const row = document.createElement("div");
        row.className = "d-flex align-items-center gap-2 mb-2 p-2 rounded";
        row.style.background = "var(--bg-elevated)";
        row.innerHTML = `<span class="text-muted-custom small" style="width:24px;">${pos + 1}.</span><span class="flex-grow-1">${q.options[optIndex]}</span>`;
        const upBtn = document.createElement("button");
        upBtn.type = "button"; upBtn.className = "btn btn-ghost btn-sm"; upBtn.innerHTML = '<i class="bi bi-arrow-up"></i>';
        upBtn.disabled = pos === 0;
        upBtn.addEventListener("click", () => { [order[pos - 1], order[pos]] = [order[pos], order[pos - 1]]; commit(); });
        const downBtn = document.createElement("button");
        downBtn.type = "button"; downBtn.className = "btn btn-ghost btn-sm"; downBtn.innerHTML = '<i class="bi bi-arrow-down"></i>';
        downBtn.disabled = pos === order.length - 1;
        downBtn.addEventListener("click", () => { [order[pos + 1], order[pos]] = [order[pos], order[pos + 1]]; commit(); });
        row.appendChild(upBtn);
        row.appendChild(downBtn);
        wrap.appendChild(row);
      });
    }
    function commit() {
      saveAnswer(q.id, JSON.stringify(order));
      render();
    }
    render();
    commit();
    return wrap;
  }

  async function saveAnswer(questionId, value) {
    answers[questionId] = value;
    try {
      await fetch(`/api/quiz/${attemptId}/answer`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: questionId, answer: value }),
      });
    } catch (err) {
      console.error("Failed to save answer", err);
    }
  }

  prevBtn.addEventListener("click", () => { if (current > 0) renderQuestion(current - 1); });
  nextBtn.addEventListener("click", () => { if (current < questions.length - 1) renderQuestion(current + 1); });

  submitBtn.addEventListener("click", () => {
    const modalEl = document.getElementById("confirmSubmitModal");
    if (modalEl && window.bootstrap && bootstrap.Modal) {
      const modalInstance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
      modalInstance.show();
    } else {
      if (confirm("Are you ready to submit your quiz?")) {
        doSubmit(false);
      }
    }
  });

  const confirmSubmitBtn = document.getElementById("confirm-submit-btn");
  if (confirmSubmitBtn) {
    confirmSubmitBtn.addEventListener("click", async () => {
      const modalEl = document.getElementById("confirmSubmitModal");
      if (modalEl && window.bootstrap && bootstrap.Modal) {
        const modalInstance = bootstrap.Modal.getInstance(modalEl);
        if (modalInstance) modalInstance.hide();
      }
      await doSubmit(false);
    });
  }

  async function doSubmit(autoSubmitted) {
    clearInterval(timerInterval);
    if (errorBox) errorBox.classList.add("d-none");
    try {
      const resp = await fetch(`/api/quiz/${attemptId}/submit`, { method: "POST" });
      const body = await resp.json();
      if (!resp.ok) {
        if (resp.status === 409 || (body.message && body.message.toLowerCase().includes("already been submitted"))) {
          window.location.href = `/quiz/attempt/${attemptId}/result`;
          return;
        }
        if (errorBox) {
          errorBox.textContent = body.message || "Could not submit the quiz.";
          errorBox.classList.remove("d-none");
        }
        return;
      }
      sessionStorage.setItem(`quiz_result_${attemptId}`, JSON.stringify(body.data));
      window.location.href = `/quiz/attempt/${attemptId}/result`;
    } catch (err) {
      if (errorBox) {
        errorBox.textContent = "Network error while submitting — your answers are saved, please retry.";
        errorBox.classList.remove("d-none");
      }
    }
  }

  function startTimerDisplay() {
    if (remainingSeconds === null) {
      timerDisplay.textContent = "Untimed";
      if (pauseBtn) pauseBtn.classList.add("d-none");
      return;
    }
    updateTimerText();
    timerInterval = setInterval(() => {
      if (isPaused) return;
      remainingSeconds--;
      updateTimerText();
      if (remainingSeconds <= 0) {
        clearInterval(timerInterval);
        if (window.OSTutor && window.OSTutor.showToast) {
          window.OSTutor.showToast("Time's up — auto-submitting.", "warning");
        }
        doSubmit(true);
      }
    }, 1000);
  }

  function updateTimerText() {
    const m = String(Math.floor(Math.max(0, remainingSeconds) / 60)).padStart(2, "0");
    const s = String(Math.max(0, remainingSeconds) % 60).padStart(2, "0");
    timerDisplay.textContent = `${m}:${s}`;
  }

  if (pauseBtn) {
    pauseBtn.addEventListener("click", async () => {
      isPaused = !isPaused;
      pauseBtn.innerHTML = isPaused ? '<i class="bi bi-play-fill"></i>' : '<i class="bi bi-pause-fill"></i>';
      await fetch(`/api/quiz/${attemptId}/${isPaused ? "pause" : "resume"}`, { method: "POST" });
    });
  }

  loadQuiz();
})();