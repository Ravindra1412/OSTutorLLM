(function () {
  "use strict";

  function wire(inputId, csvId, pdfId, urlBuilder) {
    const input = document.getElementById(inputId);
    const csvLink = document.getElementById(csvId);
    const pdfLink = document.getElementById(pdfId);
    const update = () => {
      const id = input.value.trim();
      const enabled = !!id;
      csvLink.href = enabled ? urlBuilder(id, "csv") : "#";
      pdfLink.href = enabled ? urlBuilder(id, "pdf") : "#";
      csvLink.classList.toggle("disabled", !enabled);
      pdfLink.classList.toggle("disabled", !enabled);
    };
    input.addEventListener("input", update);
    update();
  }

  wire("student-id-input", "student-csv-link", "student-pdf-link",
    (id, fmt) => `/api/faculty/students/${id}/report?format=${fmt}`);
  wire("quiz-id-input", "quiz-csv-link", "quiz-pdf-link",
    (id, fmt) => `/api/faculty/quizzes/${id}/results/download?format=${fmt}`);
})();
