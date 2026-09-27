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

  document.querySelectorAll(".entry-copy-btn").forEach(function (btn) {
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
        var label = btn.textContent;
        var copied = btn.getAttribute("data-copied") || "Copied";
        btn.textContent = copied;
        btn.setAttribute("aria-label", copied);
        setTimeout(function () {
          btn.textContent = label;
          btn.setAttribute("aria-label", label);
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

  var modal = document.getElementById("edit-entry-modal");
  var editForm = document.getElementById("edit-entry-form");
  var editContent = document.getElementById("edit-entry-content");
  var editCancel = document.getElementById("edit-entry-cancel");

  document.querySelectorAll(".entry-edit-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var card = cardFor(btn);
      if (!card || !modal || !editForm || !editContent) {
        return;
      }
      var source = card.querySelector(".entry-content-text");
      editForm.action = btn.getAttribute("data-edit-url");
      editContent.value = source ? source.textContent : "";
      modal.showModal();
    });
  });

  if (editCancel && modal) {
    editCancel.addEventListener("click", function () {
      modal.close();
    });
  }

  if (editForm) {
    editForm.addEventListener("submit", function (event) {
      event.preventDefault();
      fetch(editForm.action, {
        method: "POST",
        headers: jsonHeaders(),
        credentials: "same-origin",
        body: new FormData(editForm),
      }).then(function (response) {
        if (!response.ok) {
          throw new Error("edit failed");
        }
        return response.json();
      }).then(function (data) {
        var card = document.querySelector('[data-entry-id="' + data.item_id + '"]');
        var source = card ? card.querySelector(".entry-content-text") : null;
        if (source && data.content_text !== undefined) {
          source.textContent = data.content_text;
        }
        if (modal) {
          modal.close();
        }
      }).catch(function () {
        editForm.submit();
      });
    });
  }
})();
