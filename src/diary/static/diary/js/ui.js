(function (global) {
  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function showToast(message, type) {
    type = type || "success";
    var container = document.getElementById("toastContainer");
    if (!container) {
      return;
    }
    var toast = document.createElement("div");
    toast.className = "vd-toast pointer-events-auto " + (type === "error" ? "vd-toast-error" : "vd-toast-success");
    toast.setAttribute("role", "alert");
    toast.setAttribute("data-toast-auto-dismiss", "5000");
    toast.innerHTML =
      '<div class="flex items-center justify-between gap-3">' +
        "<span>" + escapeHtml(message) + "</span>" +
        '<button type="button" class="shrink-0 text-muted-foreground hover:text-foreground transition-colors" aria-label="Dismiss">' +
          '<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">' +
            '<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>' +
          "</svg>" +
        "</button>" +
      "</div>";
    toast.querySelector("button").addEventListener("click", function () {
      toast.remove();
    });
    container.appendChild(toast);
    setTimeout(function () {
      toast.classList.add("animate-toast-out");
      toast.addEventListener("animationend", function () {
        toast.remove();
      });
    }, 5000);
  }

  function showRecordIcon(name) {
    var iconRecord = document.getElementById("iconRecord");
    var iconPause = document.getElementById("iconPause");
    var iconResume = document.getElementById("iconResume");
    if (!iconRecord) {
      return;
    }
    iconRecord.classList.toggle("hidden", name !== "record");
    if (iconPause) {
      iconPause.classList.toggle("hidden", name !== "pause");
    }
    if (iconResume) {
      iconResume.classList.toggle("hidden", name !== "resume");
    }
  }

  function applyRecordState(state, options) {
    options = options || {};
    var recordBtn = options.recordBtn || document.getElementById("recordBtn");
    var stopBtn = options.stopBtn || document.getElementById("stopBtn");
    var spinner = options.spinner || document.getElementById("spinnerOverlay");
    var spinnerEl = document.getElementById("recordingSpinner");
    if (!recordBtn) {
      return;
    }
    recordBtn.classList.remove("recording", "paused");
    var live = state === "recording" || state === "paused";
    var busy = live || state === "uploading" || state === "processing";
    if (state === "recording") {
      recordBtn.disabled = false;
      recordBtn.classList.add("recording");
      showRecordIcon("pause");
    } else if (state === "paused") {
      recordBtn.disabled = false;
      recordBtn.classList.add("paused");
      showRecordIcon("resume");
    } else {
      recordBtn.disabled = busy;
      showRecordIcon("record");
    }
    if (stopBtn) {
      stopBtn.classList.toggle("hidden", !live);
      stopBtn.disabled = !live;
    }
    if (spinner) {
      spinner.classList.toggle("hidden", state !== "uploading" && state !== "processing");
    }
    if (spinnerEl) {
      spinnerEl.classList.toggle("vd-spinner--red", state === "uploading");
    }
  }

  document.querySelectorAll("[data-toast-auto-dismiss]").forEach(function (el) {
    var delay = parseInt(el.getAttribute("data-toast-auto-dismiss"), 10) || 5000;
    setTimeout(function () {
      el.classList.add("animate-toast-out");
      el.addEventListener("animationend", function () {
        el.remove();
      });
    }, delay);
  });

  global.VDUI = {
    showToast: showToast,
    applyRecordState: applyRecordState,
    showRecordIcon: showRecordIcon,
  };
})(window);
