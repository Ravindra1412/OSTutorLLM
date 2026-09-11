/**
 * OSTutorLLM — Tutor Chat Client Controller
 * Manages real-time interaction with the Flask /api/tutor endpoints.
 */
document.addEventListener('DOMContentLoaded', () => {
  const appContainer = document.getElementById('tutor-app');
  if (!appContainer) return;

  // DOM Elements
  const setupForm = document.getElementById('tutor-setup-form');
  const topicSelect = document.getElementById('topic-select');
  const modeSelect = document.getElementById('mode-select');
  const startBtn = document.getElementById('start-session-btn');
  const sessionBadge = document.getElementById('session-badge');
  const hintStageBadge = document.getElementById('hint-stage-badge');
  const hintProgressBar = document.getElementById('hint-progress-bar');
  const revealBtn = document.getElementById('request-reveal-btn');
  const resetBtn = document.getElementById('reset-session-btn');
  const chatMessages = document.getElementById('chat-messages');
  const chatForm = document.getElementById('chat-input-form');
  const chatInput = document.getElementById('chat-input');
  const chatSendBtn = document.getElementById('chat-send-btn');
  const chatHeaderTitle = document.getElementById('chat-header-title');
  const chatHeaderMode = document.getElementById('chat-header-mode');
  const providerBadge = document.getElementById('provider-badge');

  let currentSessionId = appContainer.dataset.activeSessionId ? parseInt(appContainer.dataset.activeSessionId, 10) : null;

  // Helper: Safe HTML escaping for user and model text
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Helper: Append a message bubble to the chat stream
  function appendMessage(sender, content, meta = {}) {
    const emptyPlaceholder = document.getElementById('chat-empty-placeholder');
    if (emptyPlaceholder) {
      emptyPlaceholder.remove();
    }

    const wrapper = document.createElement('div');
    wrapper.className = sender === 'user' 
      ? 'd-flex justify-content-end mb-2' 
      : 'd-flex justify-content-start mb-2';

    const bubble = document.createElement('div');
    bubble.className = sender === 'user'
      ? 'p-3 rounded-3 bg-primary text-white shadow-sm'
      : 'p-3 rounded-3 bg-white text-dark border shadow-sm';
    bubble.style.maxWidth = '80%';
    bubble.style.whiteSpace = 'pre-wrap';

    let headerHtml = `<div class="fw-bold small mb-1 ${sender === 'user' ? 'text-white-50' : 'text-primary'}">
      <i class="bi ${sender === 'user' ? 'bi-person-fill' : 'bi-robot'} me-1"></i>${sender === 'user' ? 'You' : 'OSTutor'}
    </div>`;

    let metaHtml = '';
    if (meta.hint_stage_label) {
      metaHtml = `<div class="mt-2 pt-1 border-top small ${sender === 'user' ? 'border-white-50 text-white-50' : 'text-muted'}">
        <span class="badge bg-secondary me-1">${escapeHtml(meta.hint_stage_label)}</span>
        ${meta.used_fallback ? '<span class="badge bg-warning text-dark">Offline Rule</span>' : ''}
      </div>`;
    }

    bubble.innerHTML = `${headerHtml}<div>${escapeHtml(content)}</div>${metaHtml}`;
    wrapper.appendChild(bubble);
    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Update UI indicators for Hint Scaffolding
  function updateScaffolding(stage, stageLabel, isFinal) {
    const stageNum = parseInt(stage, 10) || 0;
    hintStageBadge.textContent = stageLabel || `Stage ${stageNum}`;

    const percentage = Math.min(100, Math.round((stageNum / 4) * 100));
    hintProgressBar.style.width = `${percentage}%`;
    hintProgressBar.setAttribute('aria-valuenow', percentage);

    if (stageNum >= 3 && !isFinal) {
      revealBtn.disabled = false;
    } else {
      revealBtn.disabled = true;
    }
  }

  // Load existing session history if loaded via /tutor/session/<id>
  async function loadHistory(sessionId) {
    try {
      const res = await fetch(`/api/tutor/session/${sessionId}/history`);
      const resJson = await res.json();
      const data = resJson.data || resJson;
      if (res.ok && data.messages) {
        chatMessages.innerHTML = '';
        data.messages.forEach(msg => {
          appendMessage(msg.role === 'assistant' ? 'tutor' : 'user', msg.content);
        });
        sessionBadge.textContent = `Session #${sessionId}`;
        sessionBadge.className = 'badge bg-success';
        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        resetBtn.disabled = false;
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  }

  // Start Session Form Submission
  setupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const topic = topicSelect.value;
    const mode = modeSelect.value;

    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Starting...';

    try {
      const res = await fetch('/api/tutor/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, teaching_mode: mode })
      });

      const resJson = await res.json();
      const data = resJson.data || resJson;

      if (res.ok && data.session_id) {
        currentSessionId = data.session_id;
        sessionBadge.textContent = `Session #${currentSessionId}`;
        sessionBadge.className = 'badge bg-success';
        chatHeaderTitle.textContent = `Topic: ${topic}`;
        chatHeaderMode.textContent = `(${mode})`;

        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        resetBtn.disabled = false;

        chatMessages.innerHTML = '';
        const greeting = data.reply || data.initial_message || 'Hello! What questions or commands do you have about this topic?';
        appendMessage('tutor', greeting, { hint_stage_label: data.hint_stage_label || 'Introduction' });
        updateScaffolding(data.hint_stage || 0, data.hint_stage_label || 'Introduction', false);
      } else {
        alert(resJson.error || resJson.message || 'Could not start tutor session.');
      }
    } catch (err) {
      console.error('Session creation failed:', err);
      alert('Network error connecting to Tutor backend.');
    } finally {
      startBtn.disabled = false;
      startBtn.innerHTML = '<i class="bi bi-play-circle me-1"></i> Start New Session';
    }
  });

  // Message Send Submission
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text || !currentSessionId) return;

    appendMessage('user', text);
    chatInput.value = '';
    chatInput.disabled = true;
    chatSendBtn.disabled = true;

    try {
      const res = await fetch('/api/tutor/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId, message: text })
      });

      const resJson = await res.json();
      const data = resJson.data || resJson;

      if (res.ok && data.reply) {
        if (data.provider) providerBadge.textContent = data.provider;
        appendMessage('tutor', data.reply, {
          hint_stage_label: data.hint_stage_label,
          used_fallback: data.used_fallback
        });
        updateScaffolding(data.hint_stage, data.hint_stage_label, data.is_final_solution);
      } else {
        appendMessage('tutor', resJson.error || resJson.message || 'An error occurred while evaluating your message.');
      }
    } catch (err) {
      appendMessage('tutor', 'Network error: could not reach Tutor evaluation service.');
    } finally {
      chatInput.disabled = false;
      chatSendBtn.disabled = false;
      chatInput.focus();
    }
  });

  // Reveal Solution Button
  revealBtn.addEventListener('click', async () => {
    if (!currentSessionId) return;
    revealBtn.disabled = true;

    try {
      const res = await fetch('/api/tutor/reveal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId })
      });

      const resJson = await res.json();
      const data = resJson.data || resJson;

      if (res.ok && data.reply) {
        appendMessage('tutor', data.reply, { hint_stage_label: 'Complete Solution' });
        updateScaffolding(data.hint_stage, 'Solution Revealed', true);
      } else {
        alert(resJson.error || resJson.message || 'Server did not permit solution reveal.');
      }
    } catch (err) {
      alert('Network error requesting solution reveal.');
    }
  });

  // Reset Session Button
  resetBtn.addEventListener('click', async () => {
    if (!currentSessionId || !confirm('Reset this conversation?')) return;
    try {
      const res = await fetch(`/api/tutor/session/${currentSessionId}/reset`, { method: 'POST' });
      if (res.ok) {
        chatMessages.innerHTML = '';
        appendMessage('tutor', 'Conversation reset. What question or command would you like to work on next?');
        updateScaffolding(0, 'Stage 0', false);
      }
    } catch (err) {
      alert('Error resetting session.');
    }
  });

  if (currentSessionId) {
    loadHistory(currentSessionId);
  }
});