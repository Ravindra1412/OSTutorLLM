(function () {
  "use strict";
  let topicModal, lessonModal;
  document.addEventListener("DOMContentLoaded", () => {
    topicModal = new bootstrap.Modal(document.getElementById("topic-modal"));
    lessonModal = new bootstrap.Modal(document.getElementById("lesson-modal"));
  });

  async function loadTopics() {
    const resp = await fetch("/api/faculty/content/topics");
    const body = await resp.json();
    if (!resp.ok) return;
    const topics = body.data;

    const select = document.getElementById("upload-topic-select");
    select.innerHTML = topics.map(t => `<option value="${t.id}">${t.name}</option>`).join("");

    const list = document.getElementById("topics-list");
    list.innerHTML = topics.map(t => `
      <div class="card mb-2"><div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <strong>${t.name}</strong> <span class="text-muted-custom small">(${t.category}, difficulty ${t.difficulty_level})</span>
            <p class="text-muted-custom small mb-0">${t.description || ""}</p>
            <p class="small mb-0">${t.lesson_count} lesson(s)</p>
          </div>
          <div class="d-flex gap-1">
            <button class="btn btn-ghost btn-sm" data-add-lesson="${t.id}">+ Lesson</button>
            <button class="btn btn-ghost btn-sm" data-edit-topic='${JSON.stringify(t)}'>Edit</button>
            <button class="btn btn-ghost btn-sm text-danger" data-delete-topic="${t.id}">Delete</button>
          </div>
        </div>
      </div></div>`).join("");

    list.querySelectorAll("[data-add-lesson]").forEach(btn => btn.addEventListener("click", () => {
      document.getElementById("lesson-topic-id").value = btn.dataset.addLesson;
      document.getElementById("lesson-title").value = "";
      document.getElementById("lesson-summary").value = "";
      lessonModal.show();
    }));
    list.querySelectorAll("[data-edit-topic]").forEach(btn => btn.addEventListener("click", () => {
      const t = JSON.parse(btn.dataset.editTopic);
      document.getElementById("topic-id").value = t.id;
      document.getElementById("topic-name").value = t.name;
      document.getElementById("topic-category").value = t.category;
      document.getElementById("topic-description").value = t.description || "";
      document.getElementById("topic-difficulty").value = t.difficulty_level;
      topicModal.show();
    }));
    list.querySelectorAll("[data-delete-topic]").forEach(btn => btn.addEventListener("click", async () => {
      if (!confirm("Delete this topic and all its lessons?")) return;
      await fetch(`/api/faculty/content/topics/${btn.dataset.deleteTopic}`, { method: "DELETE" });
      loadTopics();
    }));
  }

  document.getElementById("topic-modal").addEventListener("show.bs.modal", (e) => {
    if (e.relatedTarget) { // "+ New Topic" button, not an edit
      document.getElementById("topic-id").value = "";
      document.getElementById("topic-name").value = "";
      document.getElementById("topic-category").value = "";
      document.getElementById("topic-description").value = "";
      document.getElementById("topic-difficulty").value = 1;
    }
  });

  document.getElementById("save-topic-btn").addEventListener("click", async () => {
    const id = document.getElementById("topic-id").value;
    const payload = {
      name: document.getElementById("topic-name").value,
      category: document.getElementById("topic-category").value,
      description: document.getElementById("topic-description").value,
      difficulty_level: parseInt(document.getElementById("topic-difficulty").value, 10),
    };
    const url = id ? `/api/faculty/content/topics/${id}` : "/api/faculty/content/topics";
    const method = id ? "PUT" : "POST";
    const resp = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (resp.ok) { topicModal.hide(); loadTopics(); } else { const b = await resp.json(); alert(b.message); }
  });

  document.getElementById("save-lesson-btn").addEventListener("click", async () => {
    const payload = {
      topic_id: parseInt(document.getElementById("lesson-topic-id").value, 10),
      title: document.getElementById("lesson-title").value,
      content_summary: document.getElementById("lesson-summary").value,
      sequence_order: parseInt(document.getElementById("lesson-order").value, 10),
    };
    const resp = await fetch("/api/faculty/content/lessons", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (resp.ok) { lessonModal.hide(); loadTopics(); } else { const b = await resp.json(); alert(b.message); }
  });

  async function loadResources() {
    const resp = await fetch("/api/faculty/content/resources");
    const body = await resp.json();
    if (!resp.ok) return;
    const list = document.getElementById("resources-list");
    list.innerHTML = body.data.length
      ? body.data.map(r => `
        <div class="d-flex justify-content-between align-items-center py-2" style="border-bottom:1px solid var(--border-subtle);">
          <span class="small">${r.original_filename} <span class="text-muted-custom">(${(r.file_size_bytes / 1024).toFixed(1)} KB)</span></span>
          <div class="d-flex gap-1">
            <a class="btn btn-ghost btn-sm" href="/api/faculty/content/resources/${r.id}/download">Download</a>
            <button class="btn btn-ghost btn-sm text-danger" data-delete-resource="${r.id}">Delete</button>
          </div>
        </div>`).join("")
      : '<p class="text-muted-custom small">No files uploaded yet.</p>';

    list.querySelectorAll("[data-delete-resource]").forEach(btn => btn.addEventListener("click", async () => {
      await fetch(`/api/faculty/content/resources/${btn.dataset.deleteResource}`, { method: "DELETE" });
      loadResources();
    }));
  }

  document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("upload-file");
    if (!fileInput.files.length) return;
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("topic_id", document.getElementById("upload-topic-select").value);
    formData.append("description", document.getElementById("upload-description").value);
    const resp = await fetch("/api/faculty/content/resources", { method: "POST", body: formData });
    if (resp.ok) { fileInput.value = ""; loadResources(); } else { const b = await resp.json(); alert(b.message); }
  });

  loadTopics();
  loadResources();
})();
