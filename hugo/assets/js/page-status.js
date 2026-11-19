(function () {
  "use strict";

  const container = document.getElementById("page-status");
  if (!container) return;

  const types = new Set(["info", "warning", "danger", "success"]);
  const displayed = new Set();
  const pagePath = normalizePath(container.dataset.pagePath);

  function normalizePath(path) {
    return path.replace(/\/+$/, "") || "/";
  }

  function parseNotices(text, source) {
    const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/);
    if (lines.shift() !== "path\ttype\tmessage") {
      throw new Error("Expected TSV header: path, type, message (tab-separated)");
    }

    const notices = [];
    lines.forEach(function (line, index) {
      if (!line.trim()) return;
      const fields = line.split("\t");
      const [path, type, message] = fields;
      if (fields.length !== 3 || !path.startsWith("/") ||
          path.startsWith("//") || /[?#\\\s]/.test(path) ||
          !types.has(type) || !message.trim()) {
        console.warn("Invalid page-status row in " + source + " at line " + (index + 2));
        return;
      }
      if (normalizePath(path) === pagePath) notices.push({ type, message });
    });
    return notices;
  }

  function displayNotices(notices) {
    notices.forEach(function ({ type, message }) {
      const key = JSON.stringify([type, message]);
      if (displayed.has(key)) return;
      displayed.add(key);

      const alert = document.createElement("div");
      alert.className = "alert alert-" + type + " alert-dismissible";
      const text = document.createElement("span");
      text.textContent = message;
      const dismiss = document.createElement("button");
      dismiss.type = "button";
      dismiss.className = "btn-close";
      dismiss.setAttribute("aria-label", "Dismiss page notice");
      dismiss.addEventListener("click", function () {
        alert.remove();
        container.hidden = container.children.length === 0;
      });
      alert.append(text, dismiss);
      container.append(alert);
      container.hidden = false;
    });
  }

  [container.dataset.localSource, container.dataset.wikiSource].forEach(function (source) {
    fetch(source, { cache: "no-cache", credentials: "omit" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.text();
      })
      .then(function (text) {
        displayNotices(parseNotices(text, source));
      })
      .catch(function (error) {
        console.warn("Could not load page notices from " + source + ":", error);
      });
  });
})();
