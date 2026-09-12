/* =====================================================================
   OSTutorLLM — main.js
   Shared, site-wide interactivity: theme toggle, sidebar toggle,
   mobile nav, toast helper, generic form validation, scroll behaviour,
   password visibility toggle.
   Loaded on every page via base.html.
   ===================================================================== */

(function () {
  "use strict";

  /* ---------------- Theme Toggle ---------------- */
  const THEME_KEY = "ostutorllm-theme";

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    document.querySelectorAll("[data-theme-icon]").forEach((el) => {
      el.className = theme === "light" ? "bi bi-moon-stars" : "bi bi-sun";
    });
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) ||
      (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    applyTheme(saved);

    document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        applyTheme(next);
        localStorage.setItem(THEME_KEY, next);
      });
    });
  }

  /* ---------------- Sidebar Toggle (desktop collapse + mobile drawer) ---------------- */
  function initSidebar() {
    const sidebar = document.querySelector(".app-sidebar");
    if (!sidebar) return;

    document.querySelectorAll("[data-sidebar-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (window.innerWidth <= 991) {
          sidebar.classList.toggle("mobile-open");
        } else {
          sidebar.classList.toggle("collapsed");
        }
      });
    });

    // Close mobile sidebar when clicking outside of it
    document.addEventListener("click", (e) => {
      if (window.innerWidth > 991) return;
      if (sidebar.classList.contains("mobile-open") &&
          !sidebar.contains(e.target) &&
          !e.target.closest("[data-sidebar-toggle]")) {
        sidebar.classList.remove("mobile-open");
      }
    });
  }

  /* ---------------- Toast Notification Helper ---------------- */
  function showToast(message, variant) {
    variant = variant || "info";
    const container = document.getElementById("toast-container");
    if (!container) return;

    const icons = { success: "bi-check-circle-fill", danger: "bi-x-circle-fill", info: "bi-info-circle-fill", warning: "bi-exclamation-triangle-fill" };
    const colors = { success: "var(--success)", danger: "var(--danger)", info: "var(--info)", warning: "var(--warning)" };

    const wrapper = document.createElement("div");
    wrapper.className = "toast align-items-center border-0 mb-2";
    wrapper.setAttribute("role", "alert");
    wrapper.setAttribute("aria-live", "assertive");
    wrapper.setAttribute("aria-atomic", "true");
    wrapper.innerHTML =
      '<div class="d-flex">' +
        '<div class="toast-body d-flex align-items-center gap-2">' +
          '<i class="bi ' + icons[variant] + '" style="color:' + colors[variant] + '"></i>' +
          '<span>' + message + '</span>' +
        '</div>' +
        '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
      '</div>';
    container.appendChild(wrapper);
    const toast = new bootstrap.Toast(wrapper, { delay: 4000 });
    toast.show();
    wrapper.addEventListener("hidden.bs.toast", () => wrapper.remove());
  }
  window.OSTutor = window.OSTutor || {};
  window.OSTutor.showToast = showToast;

  /* ---------------- Generic Bootstrap-style form validation ---------------- */
  function initFormValidation() {
    document.querySelectorAll("form[data-validate]").forEach((form) => {
      form.addEventListener("submit", (e) => {
        if (!form.checkValidity()) {
          e.preventDefault();
          e.stopPropagation();
        }
        form.classList.add("was-validated");
      });
    });
  }

  /* ---------------- Password strength (Register page) ---------------- */
  function initPasswordStrength() {
    const input = document.getElementById("password");
    const meter = document.getElementById("password-strength-bar");
    const label = document.getElementById("password-strength-label");
    if (!input || !meter) return;

    input.addEventListener("input", () => {
      const val = input.value;
      let score = 0;
      if (val.length >= 8) score++;
      if (/[A-Z]/.test(val)) score++;
      if (/[0-9]/.test(val)) score++;
      if (/[^A-Za-z0-9]/.test(val)) score++;
      const pct = (score / 4) * 100;
      const labels = ["Too weak", "Weak", "Fair", "Good", "Strong"];
      const colors = ["#F17171", "#F17171", "#FFB454", "#63D2C8", "#5FD892"];
      meter.style.width = pct + "%";
      meter.style.background = colors[score];
      if (label) label.textContent = labels[score];
    });
  }

  /* ---------------- Password Visibility Toggle ---------------- */
  function initPasswordToggle() {
    document.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-password-toggle]");
      if (!btn) return;

      const group = btn.closest(".input-group");
      if (!group) return;

      const input = group.querySelector("input");
      if (!input) return;

      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";

      const icon = btn.querySelector("i");
      if (icon) {
        icon.className = isPassword ? "bi bi-eye-slash" : "bi bi-eye";
      }
    });
  }

  /* ---------------- Copy-to-clipboard (Tutor Chat / Code blocks) ---------------- */
  function initCopyButtons() {
    document.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-copy-target]");
      if (!btn) return;
      const target = document.querySelector(btn.getAttribute("data-copy-target"));
      if (!target) return;
      navigator.clipboard.writeText(target.innerText).then(() => {
        const original = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check2"></i>';
        setTimeout(() => (btn.innerHTML = original), 1500);
        showToast("Copied to clipboard", "success");
      });
    });
  }

  /* ---------------- Navbar shadow-on-scroll ---------------- */
  function initScrollBehaviour() {
    const nav = document.querySelector(".public-navbar, .app-navbar");
    if (!nav) return;
    window.addEventListener("scroll", () => {
      nav.style.boxShadow = window.scrollY > 8 ? "0 2px 12px rgba(0,0,0,.25)" : "none";
    });
  }

  /* ---------------- Scroll-reveal for .reveal elements ---------------- */
  function initRevealOnScroll() {
    const items = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window) || items.length === 0) {
      items.forEach((el) => el.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    items.forEach((el) => observer.observe(el));
  }

  /* ---------------- Loading overlay helper (submit buttons) ---------------- */
  function initSubmitLoadingState() {
    document.querySelectorAll("form[data-loading-submit]").forEach((form) => {
      form.addEventListener("submit", () => {
        const btn = form.querySelector('[type="submit"]');
        if (!btn || !form.checkValidity()) return;
        btn.disabled = true;
        btn.dataset.originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span>';
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    initSidebar();
    initFormValidation();
    initPasswordStrength();
    initPasswordToggle();
    initCopyButtons();
    initScrollBehaviour();
    initRevealOnScroll();
    initSubmitLoadingState();

    // Initialize all Bootstrap tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => new bootstrap.Tooltip(el));
  });
})();