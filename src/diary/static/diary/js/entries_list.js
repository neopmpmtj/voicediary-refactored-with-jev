(function () {
  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function jsonHeaders() {
    return {
      "X-CSRFToken": csrfToken(),
      "X-Requested-With": "XMLHttpRequest",
      Accept: "application/json",
    };
  }

  function cardFor(el) {
    return el.closest("[data-entry-id]");
  }

  function applyEntryUpdate(card, data) {
    if (!card || !data) {
      return;
    }
    var source = card.querySelector(".entry-content-text");
    if (source && data.content_text !== undefined) {
      source.textContent = data.content_text;
    }
    var stamp = card.querySelector(".entry-modified");
    if (!stamp) {
      return;
    }
    var created = data.created_at ? Date.parse(data.created_at) : NaN;
    var updated = data.updated_at ? Date.parse(data.updated_at) : NaN;
    if (!isNaN(created) && !isNaN(updated) && updated - created >= 1000) {
      var enable = document.getElementById("edit-enable");
      var modified = enable ? enable.getAttribute("data-modified") || "modified" : "modified";
      var display = data.updated_at_display || data.updated_at;
      stamp.textContent = " · " + modified + " " + display;
      stamp.classList.remove("hidden");
    }
  }

  document.querySelectorAll(".entry-copy-btn").forEach(function (btn) {
    var label = btn.textContent;
    var ariaLabel = btn.getAttribute("aria-label") || label;
    var resetTimer = null;
    btn.addEventListener("click", function () {
      var card = cardFor(btn);
      if (!card) {
        return;
      }
      var source = card.querySelector(".entry-content-text");
      var text = source ? source.textContent : "";
      if (!text) {
        return;
      }
      navigator.clipboard.writeText(text).then(function () {
        var copied = btn.getAttribute("data-copied") || "Copied";
        btn.textContent = copied;
        btn.setAttribute("aria-label", copied);
        if (resetTimer) {
          clearTimeout(resetTimer);
        }
        resetTimer = setTimeout(function () {
          btn.textContent = label;
          btn.setAttribute("aria-label", ariaLabel);
          resetTimer = null;
        }, 2000);
      });
    });
  });

  document.querySelectorAll(".entry-delete-form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var message = form.getAttribute("data-confirm") || "Remove this entry from your voice diary?";
      if (!window.confirm(message)) {
        return;
      }
      var card = cardFor(form);
      fetch(form.action, {
        method: "POST",
        headers: jsonHeaders(),
        credentials: "same-origin",
        body: new FormData(form),
      }).then(function (response) {
        if (!response.ok) {
          throw new Error("delete failed");
        }
        if (card) {
          card.remove();
        }
      }).catch(function () {
        form.submit();
      });
    });
  });

  var editEnable = document.getElementById("edit-enable");
  var modal = document.getElementById("edit-entry-modal");
  var editForm = document.getElementById("edit-entry-form");
  var editContent = document.getElementById("edit-entry-content");
  var editCancel = document.getElementById("edit-entry-cancel");
  var editSave = document.getElementById("edit-entry-save");
  var rewriteRun = document.getElementById("rewrite-run-btn");
  var rewriteUndo = document.getElementById("rewrite-undo-btn");
  var rewriteStyle = document.getElementById("rewrite-style-select");
  var rewriteSpinner = document.getElementById("rewrite-spinner");
  var editError = document.getElementById("edit-entry-error");
  var savedText = "";

  function showEditButtons(on) {
    document.querySelectorAll(".entry-edit-btn").forEach(function (btn) {
      btn.classList.toggle("hidden", !on);
    });
  }

  function setEditError(message) {
    if (!editError) {
      return;
    }
    if (message) {
      editError.textContent = message;
      editError.classList.remove("hidden");
    } else {
      editError.textContent = "";
      editError.classList.add("hidden");
    }
  }

  function syncEditSave() {
    if (!editSave || !editContent) {
      return;
    }
    editSave.disabled = editContent.value === savedText;
  }

  function setRewriteBusy(busy) {
    if (rewriteRun) {
      rewriteRun.disabled = busy;
    }
    if (rewriteSpinner) {
      rewriteSpinner.classList.toggle("hidden", !busy);
    }
  }

  if (editEnable) {
    editEnable.addEventListener("change", function () {
      showEditButtons(editEnable.checked);
      if (!editEnable.checked && modal && modal.open) {
        modal.close();
      }
    });
  }

  document.querySelectorAll(".entry-edit-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var card = cardFor(btn);
      if (!card || !modal || !editForm || !editContent) {
        return;
      }
      var source = card.querySelector(".entry-content-text");
      savedText = source ? source.textContent : "";
      editForm.action = btn.getAttribute("data-edit-url");
      editContent.value = savedText;
      if (rewriteStyle) {
        rewriteStyle.value = "grammar";
      }
      if (rewriteUndo) {
        rewriteUndo.classList.add("hidden");
      }
      setEditError("");
      setRewriteBusy(false);
      syncEditSave();
      modal.showModal();
    });
  });

  if (editContent) {
    editContent.addEventListener("input", syncEditSave);
  }

  if (editCancel && modal) {
    editCancel.addEventListener("click", function () {
      modal.close();
    });
  }

  if (rewriteUndo) {
    rewriteUndo.addEventListener("click", function () {
      if (editContent) {
        editContent.value = savedText;
      }
      rewriteUndo.classList.add("hidden");
      setEditError("");
      syncEditSave();
    });
  }

  if (rewriteRun) {
    rewriteRun.addEventListener("click", function () {
      if (!editContent || rewriteRun.disabled) {
        return;
      }
      var text = editContent.value;
      if (!text.trim()) {
        return;
      }
      var enable = document.getElementById("edit-enable");
      var url = enable ? enable.getAttribute("data-rewrite-url") : "";
      if (!url) {
        return;
      }
      setEditError("");
      setRewriteBusy(true);
      fetch(url, {
        method: "POST",
        headers: Object.assign(jsonHeaders(), { "Content-Type": "application/json" }),
        credentials: "same-origin",
        body: JSON.stringify({
          text: text,
          style: rewriteStyle ? rewriteStyle.value : "grammar",
        }),
      }).then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) {
            throw new Error(data.message || data.error || "Rewrite failed");
          }
          return data;
        });
      }).then(function (data) {
        editContent.value = data.text;
        if (rewriteUndo) {
          rewriteUndo.classList.remove("hidden");
        }
        syncEditSave();
      }).catch(function (err) {
        setEditError(err.message || "Rewrite failed");
      }).finally(function () {
        setRewriteBusy(false);
      });
    });
  }

  if (editForm) {
    editForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (editSave && editSave.disabled) {
        return;
      }
      fetch(editForm.action, {
        method: "POST",
        headers: jsonHeaders(),
        credentials: "same-origin",
        body: new FormData(editForm),
      }).then(function (response) {
        if (!response.ok) {
          throw new Error("save failed");
        }
        return response.json();
      }).then(function (data) {
        var card = document.querySelector('[data-entry-id="' + data.item_id + '"]');
        applyEntryUpdate(card, data);
        savedText = data.content_text !== undefined ? data.content_text : savedText;
        if (rewriteUndo) {
          rewriteUndo.classList.add("hidden");
        }
        syncEditSave();
        if (modal) {
          modal.close();
        }
      }).catch(function () {
        editForm.submit();
      });
    });
  }
})();
