(function () {
  "use strict";

  async function loadNotifications() {
    const resp = await fetch("/api/faculty/notifications");
    const body = await resp.json();
    if (!resp.ok) return;
    const list = document.getElementById("notifications-list");
    list.innerHTML = body.data.length
      ? body.data.map(n => `
        <div class="d-flex justify-content-between align-items-center py-2" style="border-bottom:1px solid var(--border-subtle);">
          <span class="small ${n.is_read ? "text-muted-custom" : ""}">${n.message}</span>
          <div class="d-flex align-items-center gap-2">
            <span class="text-muted-custom small">${new Date(n.created_at).toLocaleString()}</span>
            ${n.is_read ? "" : `<button class="btn btn-ghost btn-sm" data-mark-read="${n.id}">Mark read</button>`}
          </div>
        </div>`).join("")
      : '<p class="text-muted-custom small">No notifications.</p>';

    list.querySelectorAll("[data-mark-read]").forEach(btn => btn.addEventListener("click", async () => {
      await fetch(`/api/faculty/notifications/${btn.dataset.markRead}/read`, { method: "POST" });
      loadNotifications();
    }));
  }

  document.getElementById("send-announcement-btn").addEventListener("click", async () => {
    const input = document.getElementById("announcement-input");
    if (!input.value.trim()) return;
    const resp = await fetch("/api/faculty/announcements", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: input.value.trim() }),
    });
    const body = await resp.json();
    if (resp.ok) {
      const msg = document.getElementById("announcement-sent-msg");
      msg.textContent = `Sent to ${body.data.recipient_count} student(s).`;
      msg.classList.remove("d-none");
      input.value = "";
    }
  });

  loadNotifications();
})();
