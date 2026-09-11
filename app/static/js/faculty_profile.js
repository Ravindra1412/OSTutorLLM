(function () {
  "use strict";

  async function load() {
    const resp = await fetch("/api/faculty/profile");
    const body = await resp.json();
    if (!resp.ok) return;
    const d = body.data;
    document.getElementById("p-name").value = d.name || "";
    document.getElementById("p-email").value = d.email || "";
    document.getElementById("p-department").value = d.department || "";
    document.getElementById("p-title").value = d.title || "";
    document.getElementById("p-subjects").value = d.subjects_taught || "";
    document.getElementById("p-bio").value = d.bio || "";
  }

  document.getElementById("save-profile-btn").addEventListener("click", async () => {
    const payload = {
      name: document.getElementById("p-name").value,
      department: document.getElementById("p-department").value,
      title: document.getElementById("p-title").value,
      subjects_taught: document.getElementById("p-subjects").value,
      bio: document.getElementById("p-bio").value,
    };
    const resp = await fetch("/api/faculty/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (resp.ok) {
      document.getElementById("profile-saved-msg").classList.remove("d-none");
      setTimeout(() => document.getElementById("profile-saved-msg").classList.add("d-none"), 2000);
    }
  });

  document.getElementById("change-password-btn").addEventListener("click", async () => {
    const current_password = document.getElementById("current-password").value;
    const new_password = document.getElementById("new-password").value;
    const resp = await fetch("/api/faculty/profile/change-password", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ current_password, new_password }),
    });
    const body = await resp.json();
    const msg = document.getElementById("password-msg");
    msg.textContent = body.message;
    msg.className = resp.ok ? "small mt-2 text-success" : "small mt-2 text-danger";
    if (resp.ok) {
      document.getElementById("current-password").value = "";
      document.getElementById("new-password").value = "";
    }
  });

  load();
})();
