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
          item.textContent = file.name;
          var remove = document.createElement("button");
          remove.type = "button";
          remove.textContent = "Remove";
          remove.addEventListener("click", function () {
            files.splice(index, 1);
            render();
            onChange(files.slice());
          });
          item.appendChild(remove);
          list.appendChild(item);
        });
      }
      if (badge) {
        badge.hidden = files.length === 0;
        badge.textContent = String(files.length);
      }
    }

    if (button && input && button.tagName === "BUTTON") {
      button.addEventListener("click", function () {
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
