(function (global) {
  function DiaryAttachments(options) {
    var input = document.getElementById(options.inputId || "attachInput");
    var button = document.getElementById(options.buttonId || "attachBtn");
    var list = document.getElementById(options.listId || "attachList");
    var badge = document.getElementById(options.badgeId || "attachBadge");
    var onChange = options.onChange || function () {};
    var files = [];

    function render() {
      if (list) {
        list.innerHTML = "";
        files.forEach(function (file, index) {
          var item = document.createElement("li");
          item.className = "flex items-center justify-between gap-2 text-sm";
          var name = document.createElement("span");
          name.className = "truncate";
          name.textContent = file.name;
          var remove = document.createElement("button");
          remove.type = "button";
          remove.className = "text-destructive hover:text-destructive/80 text-xs shrink-0";
          remove.setAttribute("aria-label", "Remove");
          remove.textContent = "Remove";
          remove.addEventListener("click", function () {
            files.splice(index, 1);
            render();
            onChange(files.slice());
          });
          item.appendChild(name);
          item.appendChild(remove);
          list.appendChild(item);
        });
      }
      if (badge) {
        if (files.length > 0) {
          badge.classList.remove("hidden");
          badge.classList.add("flex");
          badge.hidden = false;
          badge.textContent = String(files.length);
        } else {
          badge.classList.add("hidden");
          badge.classList.remove("flex");
          badge.hidden = true;
          badge.textContent = "0";
        }
      }
    }

    if (button && input) {
      button.addEventListener("click", function (event) {
        event.preventDefault();
        input.click();
      });
    }
    if (input) {
      input.addEventListener("change", function () {
        Array.prototype.forEach.call(input.files || [], function (file) {
          files.push(file);
        });
        input.value = "";
        render();
        onChange(files.slice());
      });
    }

    return {
      files: function () {
        return files.slice();
      },
      clear: function () {
        files = [];
        render();
        onChange(files.slice());
      },
    };
  }

  global.DiaryAttachments = DiaryAttachments;
})(window);
