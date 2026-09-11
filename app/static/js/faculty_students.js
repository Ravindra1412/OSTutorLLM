(function () {
  "use strict";
  const tbody = document.getElementById("students-tbody");
  const emptyMsg = document.getElementById("empty-msg");
  const searchInput = document.getElementById("search-input");
  const activeCheck = document.getElementById("active-only-check");
  let debounceTimer = null;

  function render(students) {
    tbody.innerHTML = "";
    emptyMsg.style.display = students.length ? "none" : "block";
    students.forEach((s) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${s.name}</td>
        <td class="text-muted-custom">${s.email}</td>
        <td>${s.level}</td>
        <td>${s.xp_total}</td>
        <td>${s.overall_learning_score != null ? s.overall_learning_score.toFixed(1) : "—"}</td>
        <td class="text-muted-custom small">${s.last_login_at ? new Date(s.last_login_at).toLocaleDateString() : "Never"}</td>
        <td><a href="/faculty/students/${s.id}" class="btn btn-outline-accent btn-sm">View</a></td>`;
      tbody.appendChild(tr);
    });
  }

  async function load() {
    const params = new URLSearchParams();
    if (searchInput.value.trim()) params.set("search", searchInput.value.trim());
    if (activeCheck.checked) params.set("active_only", "true");
    const resp = await fetch(`/api/faculty/students?${params}`);
    const body = await resp.json();
    if (resp.ok) render(body.data.students);
  }

  searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(load, 300);
  });
  activeCheck.addEventListener("change", load);
  load();
})();
