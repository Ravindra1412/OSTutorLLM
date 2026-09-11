(function () {
  "use strict";

  async function loadAISettings() {
    const resp = await fetch("/api/faculty/ai-tutor/settings");
    const body = await resp.json();
    if (!resp.ok) return;
    const d = body.data;
    document.getElementById("ai-enabled").checked = d.ai_tutor_enabled;
    document.getElementById("ai-difficulty").value = d.default_difficulty;
    document.getElementById("ai-max-hint").value = d.max_hint_stage;
    const select = document.getElementById("ai-teaching-mode");
    select.innerHTML = d.available_teaching_modes.map(m => `<option value="${m}" ${m === d.default_teaching_mode ? "selected" : ""}>${m}</option>`).join("");

    const usageResp = await fetch("/api/faculty/ai-tutor/usage");
    const usageBody = await usageResp.json();
    if (usageResp.ok) document.getElementById("ai-usage-total").textContent = usageBody.data.total_sessions;
  }

  document.getElementById("save-ai-settings-btn").addEventListener("click", async () => {
    const payload = {
      ai_tutor_enabled: document.getElementById("ai-enabled").checked,
      default_difficulty: parseInt(document.getElementById("ai-difficulty").value, 10),
      max_hint_stage: parseInt(document.getElementById("ai-max-hint").value, 10),
      default_teaching_mode: document.getElementById("ai-teaching-mode").value,
    };
    const resp = await fetch("/api/faculty/ai-tutor/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!resp.ok) { const b = await resp.json(); alert(b.message); }
  });

  async function loadAccountSettings() {
    const resp = await fetch("/api/settings/account");
    const body = await resp.json();
    if (!resp.ok) return;
    const d = body.data;
    document.getElementById("account-theme").value = d.theme;
    document.getElementById("account-email-notif").checked = d.email_notifications_enabled;
    document.getElementById("account-achievement-notif").checked = d.achievement_notifications_enabled;
  }

  document.getElementById("save-account-settings-btn").addEventListener("click", async () => {
    const payload = {
      theme: document.getElementById("account-theme").value,
      email_notifications_enabled: document.getElementById("account-email-notif").checked,
      achievement_notifications_enabled: document.getElementById("account-achievement-notif").checked,
    };
    await fetch("/api/settings/account", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  });

  async function loadSecuritySettings() {
    const resp = await fetch("/api/faculty/settings/security");
    const body = await resp.json();
    if (!resp.ok) return;
    document.getElementById("sec-session").textContent = body.data.session_lifetime_hours;
    document.getElementById("sec-password").textContent = body.data.min_password_length;
    document.getElementById("sec-rate").textContent = body.data.rate_limit_per_minute;
  }

  async function loadBackups() {
    const resp = await fetch("/api/faculty/settings/backup");
    const body = await resp.json();
    if (!resp.ok) return;
    const list = document.getElementById("backups-list");
    if (!body.data.supported) {
      list.innerHTML = '<p class="text-muted-custom small mb-0">Automatic backup is only supported for the SQLite database in this phase.</p>';
      document.getElementById("trigger-backup-btn").disabled = true;
      return;
    }
    list.innerHTML = body.data.existing_backups.length
      ? body.data.existing_backups.map(b => `
        <div class="d-flex justify-content-between small mb-1">
          <span>${b.filename} (${(b.size_bytes / 1024).toFixed(1)} KB)</span>
          <a href="/api/faculty/settings/backup/${b.filename}/download">Download</a>
        </div>`).join("")
      : '<p class="text-muted-custom small mb-0">No backups yet.</p>';
  }

  document.getElementById("trigger-backup-btn").addEventListener("click", async () => {
    const resp = await fetch("/api/faculty/settings/backup", { method: "POST" });
    if (resp.ok) loadBackups();
  });

  loadAISettings();
  loadAccountSettings();
  loadSecuritySettings();
  loadBackups();
})();
