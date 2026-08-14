(function () {
  "use strict";

  const form = document.getElementById("watermark-form");
  if (!form) return;

  const fileInput = document.getElementById("pdf");
  const dropZone = document.getElementById("pdf-drop-zone");
  const fileSummary = document.getElementById("pdf-file-summary");
  const footerInput = document.getElementById("footer-text");
  const pageStartInput = document.getElementById("page-start");
  const bottomMarginInput = document.getElementById("bottom-margin");
  const footerSizeInput = document.getElementById("footer-size");
  const pageNumberSizeInput = document.getElementById("page-number-size");
  const lineSpacingInput = document.getElementById("line-spacing");
  const previewPage = document.getElementById("watermark-preview-page");
  const previewCanvas = document.getElementById("watermark-preview-canvas");
  const previewPlaceholder = document.getElementById("watermark-preview-placeholder");
  const previewPlaceholderText = document.getElementById("watermark-preview-placeholder-text");
  const previewFooter = document.getElementById("watermark-preview-footer");
  const previewNumber = document.getElementById("watermark-preview-number");
  const submitButton = document.getElementById("generate-pdf");
  const submitLabel = document.getElementById("generate-label");
  const submitIcon = document.getElementById("generate-icon");
  const submitSpinner = document.getElementById("generate-spinner");
  const status = document.getElementById("watermark-status");
  const maxFileSize = 25 * 1024 * 1024;
  const pdfLibraryUrl = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.min.mjs";
  const pdfWorkerUrl = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.min.mjs";
  let pdfLibraryPromise = null;
  let previewGeneration = 0;
  let previewLoadingTask = null;
  let previewRenderTask = null;
  let resizeTimer = null;

  function setStatus(message, state) {
    status.textContent = message;
    status.classList.toggle("text-success", state === "success");
    status.classList.toggle("text-danger", state === "error");
    status.classList.toggle("text-muted", !state);
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function validateFile(file) {
    if (!file) return "Choose a PDF first.";
    if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
      return "The selected file must be a PDF.";
    }
    if (file.size > maxFileSize) return "The PDF exceeds the 25 MB limit.";
    return "";
  }

  function updateFileSummary() {
    const file = fileInput.files[0];
    const error = validateFile(file);
    fileInput.setCustomValidity(error);
    fileSummary.textContent = file ? `${file.name} · ${formatBytes(file.size)}` : "No file selected";
    if (file && error) setStatus(error, "error");
    else if (file) setStatus("Ready", "success");
  }

  function getPdfLibrary() {
    if (!pdfLibraryPromise) {
      pdfLibraryPromise = import(pdfLibraryUrl).then((pdfLibrary) => {
        pdfLibrary.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;
        return pdfLibrary;
      });
    }
    return pdfLibraryPromise;
  }

  async function updateDocumentPreview() {
    const generation = ++previewGeneration;
    previewRenderTask?.cancel();
    previewRenderTask = null;
    if (previewLoadingTask) {
      await previewLoadingTask.destroy().catch(() => {});
      previewLoadingTask = null;
    }

    previewCanvas.hidden = true;
    previewPlaceholder.hidden = false;
    previewPlaceholderText.textContent = "Choose a PDF to preview its first page";

    const file = fileInput.files[0];
    if (!file || validateFile(file)) return;

    previewPlaceholderText.textContent = "Rendering first page…";
    try {
      const pdfLibrary = await getPdfLibrary();
      const data = new Uint8Array(await file.arrayBuffer());
      if (generation !== previewGeneration) return;

      previewLoadingTask = pdfLibrary.getDocument({
        data,
        isOffscreenCanvasSupported: false,
      });
      const documentPreview = await previewLoadingTask.promise;
      const firstPage = await documentPreview.getPage(1);
      if (generation !== previewGeneration) return;

      const initialViewport = firstPage.getViewport({ scale: 1 });
      const cssScale = Math.min(
        previewPage.clientWidth / initialViewport.width,
        previewPage.clientHeight / initialViewport.height
      );
      const viewport = firstPage.getViewport({ scale: cssScale });
      const outputScale = Math.min(window.devicePixelRatio || 1, 2);
      previewCanvas.width = Math.floor(viewport.width * outputScale);
      previewCanvas.height = Math.floor(viewport.height * outputScale);
      previewCanvas.style.width = `${Math.floor(viewport.width)}px`;
      previewCanvas.style.height = `${Math.floor(viewport.height)}px`;

      const context = previewCanvas.getContext("2d", { alpha: false });
      const transform = outputScale === 1
        ? null
        : [outputScale, 0, 0, outputScale, 0, 0];
      const originalRequestAnimationFrame = window.requestAnimationFrame;
      const originalCancelAnimationFrame = window.cancelAnimationFrame;
      window.requestAnimationFrame = (callback) => window.setTimeout(
        () => callback(window.performance.now()),
        0
      );
      window.cancelAnimationFrame = (timer) => window.clearTimeout(timer);
      try {
        previewRenderTask = firstPage.render({
          canvasContext: context,
          transform,
          viewport,
        });
        await previewRenderTask.promise;
      } finally {
        window.requestAnimationFrame = originalRequestAnimationFrame;
        window.cancelAnimationFrame = originalCancelAnimationFrame;
      }
      if (generation !== previewGeneration) return;
      previewCanvas.hidden = false;
      previewPlaceholder.hidden = true;
      await documentPreview.cleanup();
    } catch (error) {
      if (error?.name === "RenderingCancelledException") return;
      previewPlaceholderText.textContent = "This PDF could not be previewed";
      console.warn("Could not render PDF preview", error);
    } finally {
      previewRenderTask = null;
    }
  }

  function normalizeFooter(value) {
    return value.normalize("NFC").replace(/\r\n?/g, "\n").replace(/\t/g, " ");
  }

  function validateFooter(value) {
    if (value.split("\n").length > 8) return "The footer can contain at most eight lines.";
    const withoutTags = value.replace(/<\/?i>/g, "");
    if (/[<>]/.test(withoutTags)) return "Only <i> and </i> markup is supported.";

    let italicOpen = false;
    for (const tag of value.match(/<\/?i>/g) || []) {
      if (tag === "<i>") {
        if (italicOpen) return "Italic tags cannot be nested.";
        italicOpen = true;
      } else if (!italicOpen) {
        return "The footer contains an unmatched </i> tag.";
      } else {
        italicOpen = false;
      }
    }
    return italicOpen ? "The footer contains an unmatched <i> tag." : "";
  }

  function escapeHtml(value) {
    const element = document.createElement("span");
    element.textContent = value;
    return element.innerHTML;
  }

  function renderFooter(value) {
    return escapeHtml(value)
      .replace(/&lt;i&gt;/g, "<i>")
      .replace(/&lt;\/i&gt;/g, "</i>")
      .replace(/\n/g, "<br>");
  }

  function numberValue(input, fallback) {
    const value = Number.parseFloat(input.value);
    return Number.isFinite(value) ? value : fallback;
  }

  function updatePreview() {
    const footer = normalizeFooter(footerInput.value);
    const footerError = validateFooter(footer);
    const hasOperation = Boolean(footer || pageStartInput.value.trim());
    footerInput.setCustomValidity(
      footerError || (hasOperation ? "" : "Enter footer text or a starting page number.")
    );
    previewFooter.innerHTML = footer ? renderFooter(footer) : "Footer preview";
    previewFooter.classList.toggle("text-muted", !footer);
    previewNumber.textContent = pageStartInput.value.trim();

    const pageHeight = previewPage.clientHeight || 400;
    const bottomOffset = numberValue(bottomMarginInput, 14);
    const footerSize = numberValue(footerSizeInput, 9);
    const numberSize = numberValue(pageNumberSizeInput, 11);
    const lineSpacing = numberValue(lineSpacingInput, 1.2);
    const footerLines = Math.max(1, footer.split("\n").length);
    const scale = pageHeight / 792;
    const footerBottom = Math.max(6, bottomOffset * scale);
    const footerPixels = Math.max(8, footerSize * scale);
    const numberPixels = Math.max(9, numberSize * scale);
    const numberBottom = footerBottom + footerLines * footerPixels * lineSpacing + .6 * footerPixels;

    previewFooter.style.bottom = `${footerBottom}px`;
    previewFooter.style.fontSize = `${footerPixels}px`;
    previewFooter.style.lineHeight = String(lineSpacing);
    previewNumber.style.bottom = `${numberBottom}px`;
    previewNumber.style.fontSize = `${numberPixels}px`;
  }

  function setWorking(working) {
    submitButton.disabled = working;
    submitLabel.textContent = working ? "Generating…" : "Generate PDF";
    submitIcon.classList.toggle("d-none", working);
    submitSpinner.classList.toggle("d-none", !working);
  }

  dropZone.addEventListener("keydown", function (event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  for (const eventName of ["dragenter", "dragover"]) {
    dropZone.addEventListener(eventName, function (event) {
      event.preventDefault();
      dropZone.classList.add("is-dragging");
    });
  }

  for (const eventName of ["dragleave", "drop"]) {
    dropZone.addEventListener(eventName, function (event) {
      event.preventDefault();
      dropZone.classList.remove("is-dragging");
    });
  }

  dropZone.addEventListener("drop", function (event) {
    if (event.dataTransfer.files.length) {
      fileInput.files = event.dataTransfer.files;
      updateFileSummary();
      updateDocumentPreview();
    }
  });

  fileInput.addEventListener("change", function () {
    updateFileSummary();
    updateDocumentPreview();
  });
  for (const input of [footerInput, pageStartInput, bottomMarginInput, footerSizeInput, pageNumberSizeInput, lineSpacingInput]) {
    input.addEventListener("input", updatePreview);
  }
  window.addEventListener("resize", function () {
    updatePreview();
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(updateDocumentPreview, 150);
  });

  form.addEventListener("reset", function () {
    window.requestAnimationFrame(function () {
      fileInput.setCustomValidity("");
      footerInput.setCustomValidity("");
      fileSummary.textContent = "No file selected";
      setStatus("", "");
      updateDocumentPreview();
      updatePreview();
    });
  });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    updateFileSummary();
    updatePreview();
    if (!form.reportValidity()) return;

    setWorking(true);
    setStatus("Uploading and processing…", "");
    try {
      const formData = new FormData(form);
      formData.set("footer_text", normalizeFooter(footerInput.value));
      const response = await fetch(form.action, { method: "POST", body: formData });
      const contentType = response.headers.get("content-type") || "";
      if (!response.ok || !contentType.startsWith("application/pdf")) {
        if (contentType.startsWith("text/plain")) {
          const message = (await response.text()).trim();
          throw new Error(message || `Request failed with status ${response.status}.`);
        }
        if (!response.ok) {
          throw new Error(`PDF service unavailable (HTTP ${response.status}).`);
        }
        const responseType = contentType.split(";", 1)[0] || "unknown content type";
        throw new Error(`PDF service returned ${responseType} instead of a PDF.`);
      }
      const pdf = await response.blob();
      if (!pdf.size) {
        throw new Error(`PDF service unavailable (HTTP ${response.status}).`);
      }

      const downloadUrl = URL.createObjectURL(pdf);
      const download = document.createElement("a");
      const inputName = fileInput.files[0].name.replace(/\.pdf$/i, "");
      download.href = downloadUrl;
      download.download = `${inputName}.watermarked.pdf`;
      document.body.appendChild(download);
      download.click();
      download.remove();
      window.setTimeout(function () { URL.revokeObjectURL(downloadUrl); }, 1000);
      setStatus("PDF generated", "success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not generate the PDF.";
      setStatus(message.slice(0, 240), "error");
    } finally {
      setWorking(false);
    }
  });

  updatePreview();
})();