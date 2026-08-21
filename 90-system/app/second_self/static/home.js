"use strict";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("textarea[data-char-count]").forEach((textarea) => {
    const max = Number(textarea.getAttribute("maxlength") || 0);
    const counter = document.querySelector(
      `[data-char-count-for="${textarea.id}"]`
    );
    if (!counter || !max) return;
    const update = () => {
      counter.textContent = `${textarea.value.length} / ${max}`;
    };
    textarea.addEventListener("input", update);
    update();
  });

  const statElements = document.querySelectorAll("[data-stat]");
  if (statElements.length === 0) return;
  const refreshStats = async () => {
    try {
      const response = await fetch("/stats", {
        headers: { "Accept": "application/json" },
        cache: "no-store",
      });
      if (!response.ok) return;
      const stats = await response.json();
      statElements.forEach((element) => {
        const key = element.getAttribute("data-stat");
        if (key in stats) {
          element.textContent = String(stats[key]);
        }
      });
    } catch {
      // Keep the server-rendered counts if the fetch fails.
    }
  };
  window.setInterval(refreshStats, 60_000);
  refreshStats();
});

document.addEventListener("keydown", (event) => {
  const target = event.target;
  const isTyping =
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    (target instanceof HTMLElement && target.isContentEditable);
  if (isTyping) return;

  const key = event.key.toLowerCase();
  if (key === "/") {
    const searchInput = document.querySelector("#query");
    if (searchInput) {
      event.preventDefault();
      searchInput.focus();
    }
    return;
  }

  if (event.ctrlKey || event.metaKey || event.altKey) return;

  const shortcuts = {
    c: "/capture",
    j: "/journal",
    t: "/tags",
    d: "/due",
    r: "/recent",
  };
  if (shortcuts[key]) {
    event.preventDefault();
    window.location.href = shortcuts[key];
    return;
  }

  if (key === "g") {
    const homeLink = document.querySelector('a[href="/"]');
    if (homeLink) {
      event.preventDefault();
      window.location.href = "/";
    }
  }
});

document.addEventListener("click", async (event) => {
  const dismissButton = event.target.closest("[data-dismiss]");
  if (dismissButton) {
    const notice = dismissButton.closest(".notice");
    if (notice) {
      notice.classList.add("notice-hiding");
      window.setTimeout(() => {
        notice.remove();
      }, 180);
    }
    return;
  }

  const copyButton = event.target.closest("[data-copy]");
  if (copyButton) {
    const value = copyButton.getAttribute("data-copy");
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      const original = copyButton.textContent;
      copyButton.textContent = "Copied";
      window.setTimeout(() => {
        copyButton.textContent = original;
      }, 1400);
    } catch {
      copyButton.textContent = "Copy unavailable";
    }
    return;
  }

  const openTrigger = event.target.closest("[data-open]");
  if (openTrigger) {
    const dialogId = openTrigger.getAttribute("data-open");
    const dialog = document.getElementById(dialogId);
    if (dialog && typeof dialog.showModal === "function") {
      dialog.showModal();
    }
    return;
  }

  const closeTrigger = event.target.closest("[data-close]");
  if (closeTrigger) {
    const dialogId = closeTrigger.getAttribute("data-close");
    const dialog = document.getElementById(dialogId);
    if (dialog && typeof dialog.close === "function") {
      dialog.close();
    }
    return;
  }

  const dropdownToggle = event.target.closest("[data-tag-dropdown-toggle]");
  if (dropdownToggle) {
    const dropdown = dropdownToggle.closest("[data-tag-dropdown]");
    const list = dropdown ? dropdown.querySelector(".tag-dropdown-list") : null;
    if (list) {
      list.hidden = !list.hidden;
    }
    return;
  }

  const option = event.target.closest("[data-tag-value]");
  if (option) {
    const dropdown = option.closest("[data-tag-dropdown]");
    if (dropdown) {
      const toggle = dropdown.querySelector(".tag-dropdown-toggle");
      const input = dropdown.querySelector("input[name='old_tag']");
      const list = dropdown.querySelector(".tag-dropdown-list");
      if (toggle) toggle.textContent = option.getAttribute("data-tag-value");
      if (input) input.value = option.getAttribute("data-tag-value") || "";
      if (list) list.hidden = true;
    }
  }
});
