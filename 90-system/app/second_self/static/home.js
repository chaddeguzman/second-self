"use strict";

document.addEventListener("click", async (event) => {
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
