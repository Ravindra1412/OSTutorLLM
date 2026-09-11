/* =====================================================================
   OSTutorLLM — code_review_engine.js (Part 3.8)
   Drives the Code Review editor page: submit for review, render
   feedback (blocked/safety, static findings, LLM improvements, score
   card), request staged hints one at a time, and show the resubmission
   comparison (Section 10) once a session has 2+ submissions.
   ===================================================================== */

(function () {
  "use strict";

  const container = document.querySelector("[data-session-id]");
  if (!container) return;

  let sessionId = container.getAttribute("data-session-id") || null;
  let currentSubmissionId = null;

  const topicSelect = document.getElementById("topic-select");
  const scriptInput = document.getElementById("script-input");
  const feedbackOutput = document.getElementById("feedback-output");
  const scoreCardInline = document.getElementById("score-card-inline");
  const submitBtn = document.getElementById("submit-btn");
  const compareBtn = document.getElementById("compare-btn");
  const comparisonPanel = document.getElementById("comparison-panel");

  function escapeHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function severityIcon(sev) {
    return { error: "bi-x-circle-fill", warning: "bi-exclamation-triangle-fill", info: "bi-info-circle-fill" }[sev] || "bi-dot";
  }
  function severityColor(sev) {
    return { error: "var(--danger)", warning: "var(--amber-500)", info: "var(--cyan-400)" }[sev] || "var(--text-muted)";
  }

  async function submitForReview() {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span>';
    feedbackOutput.innerHTML = `<div class="text-center text-muted-custom py-5">Analyzing your script...</div>`;

    try {
      const resp = await fetch("/api/code-review/submit", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topicSelect.value, code: scriptInput.value, session_id: sessionId ? parseInt(sessionId, 10) : null }),
      });
      const body = await resp.json();

      if (!resp.ok) {
        feedbackOutput.innerHTML = `<div class="alert" style="background:var(--bg-elevated);border:1px solid var(--danger);">${body.message}</div>`;
        return;
      }

      if (body.data.blocked) {
        renderBlocked(body.data);
      } else {
        sessionId = body.data.session_id;
        container.setAttribute("data-session-id", sessionId);
        history.replaceState(null, "", `/code-review/session/${sessionId}`);
        currentSubmissionId = body.data.submission.submission_id;
        renderFeedback(body.data.submission);
        if (body.data.submission.submission_number > 1) compareBtn.style.display = "inline-block";
      }
    } catch (err) {
      feedbackOutput.innerHTML = `<div class="alert" style="background:var(--bg-elevated);border:1px solid var(--danger);">Network error — please try again.</div>`;
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="bi bi-search me-1"></i>Submit for Review';
    }
  }

  function renderBlocked(data) {
    feedbackOutput.innerHTML = `
      <div class="alert" style="background:var(--bg-elevated);border:1px solid var(--danger);color:var(--text-primary);">
        <h6 class="mb-2"><i class="bi bi-shield-exclamation text-accent me-2"></i>Not Reviewed — Safety Concern</h6>
        <p class="mb-0">${escapeHtml(data.explanation)}</p>
      </div>`;
    scoreCardInline.innerHTML = "";
  }

  function renderFeedback(submission) {
    const f = submission.feedback || {};
    let html = "";

    if (f.strengths && f.strengths.length) {
      html += `<div class="feedback-item resolved mb-3"><div class="fw-semibold small mb-1"><i class="bi bi-check-circle text-success me-1"></i>What you did well</div><ul class="mb-0 small">${f.strengths.map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ul></div>`;
    }

    (submission.static_findings || []).forEach((finding, i) => {
      html += `
        <div class="feedback-item mb-2" data-finding-index="${i}">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <div class="fw-semibold small mb-1"><i class="bi ${severityIcon(finding.severity)} me-1" style="color:${severityColor(finding.severity)};"></i>${escapeHtml(finding.category.replace(/_/g, " "))}${finding.line_number ? ` · Line ${finding.line_number}` : ""}</div>
              <p class="mb-0 small">${escapeHtml(finding.message)}</p>
            </div>
          </div>
        </div>`;
    });

    if (f.improvements && f.improvements.length) {
      html += `<div class="mt-3"><div class="fw-semibold small mb-2"><i class="bi bi-lightbulb text-accent me-1"></i>Improvement Directions</div>`;
      f.improvements.forEach(imp => {
        html += `<div class="feedback-item mb-2"><p class="mb-1 small fw-semibold">${escapeHtml(imp.issue || "")}</p><p class="mb-1 small text-muted-custom">${escapeHtml(imp.why_it_matters || "")}</p><p class="mb-0 small">${escapeHtml(imp.direction || "")}</p></div>`;
      });
      html += `</div>`;
    }

    if (f.best_practices_note) {
      html += `<div class="feedback-item mt-3"><div class="fw-semibold small mb-1"><i class="bi bi-mortarboard text-accent me-1"></i>Best Practices</div><p class="mb-0 small">${escapeHtml(f.best_practices_note)}</p></div>`;
    }

    html += `<div class="mt-3 d-flex gap-2">
      <button class="btn btn-outline-accent btn-sm" id="hint-btn"><i class="bi bi-lightbulb me-1"></i>Get a Hint</button>
    </div>
    <div id="hint-output" class="mt-2"></div>`;

    feedbackOutput.innerHTML = html;

    document.getElementById("hint-btn").addEventListener("click", requestHint);
    renderScoreCard(submission.scores);
  }

  function renderScoreCard(scores) {
    if (!scores) { scoreCardInline.innerHTML = ""; return; }
    scoreCardInline.innerHTML = `
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <span class="badge-tier badge-gold">Overall: ${scores.overall}%</span>
        ${Object.entries(scores).filter(([k]) => k !== "overall").map(([k, v]) =>
          `<span class="badge-tier badge-locked" title="${k}">${k.replace(/_/g, " ")}: ${v}</span>`
        ).join("")}
      </div>`;
  }

  async function requestHint() {
    const hintBtn = document.getElementById("hint-btn");
    const hintOutput = document.getElementById("hint-output");
    hintBtn.disabled = true;

    const resp = await fetch(`/api/code-review/submission/${currentSubmissionId}/hint`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}),
    });
    const body = await resp.json();
    hintBtn.disabled = false;

    if (!resp.ok) { hintOutput.innerHTML = `<div class="text-danger small">${body.message}</div>`; return; }

    const stageLabel = body.data.hint_stage >= 4 ? "Final Guidance" : `Hint ${body.data.hint_stage}/3`;
    hintOutput.innerHTML += `
      <div class="feedback-item hint-bubble mb-2">
        <div class="hint-tag"><i class="bi bi-lightbulb"></i>${stageLabel}</div>
        <p class="mb-0 small">${escapeHtml(body.data.text)}</p>
      </div>`;

    if (body.data.hint_stage >= 4) hintBtn.style.display = "none";
  }

  async function showComparison() {
    const resp = await fetch(`/api/code-review/session/${sessionId}/compare`);
    const body = await resp.json();
    if (!resp.ok) { window.OSTutor && window.OSTutor.showToast(body.message, "danger"); return; }

    document.getElementById("improvement-summary").textContent = body.data.improvement_summary;
    document.getElementById("diff-output").textContent = body.data.diff_lines.join("\n");
    comparisonPanel.style.display = "block";
    comparisonPanel.scrollIntoView({ behavior: "smooth" });
  }

  submitBtn.addEventListener("click", submitForReview);
  compareBtn.addEventListener("click", showComparison);

  // If loaded on an existing session page, fetch and render its latest submission.
  if (sessionId) {
    fetch(`/api/code-review/session/${sessionId}`).then(r => r.json()).then(body => {
      if (body.data && body.data.submissions.length) {
        const latest = body.data.submissions[body.data.submissions.length - 1];
        scriptInput.value = latest.code_text;
        currentSubmissionId = latest.submission_id;
        renderFeedback(latest);
        if (body.data.submissions.length > 1) compareBtn.style.display = "inline-block";
      }
    });
  }
})();
