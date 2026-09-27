(function () {
  var config = JSON.parse(document.getElementById("recorder-config").textContent);
  var timer = document.getElementById("timer");
  var status = document.getElementById("status");
  var toast = document.getElementById("toast");
  var result = document.getElementById("result");
  var recordBtn = document.getElementById("recordBtn");
  var pauseBtn = document.getElementById("pauseBtn");
  var stopBtn = document.getElementById("stopBtn");
  var saveFilesBtn = document.getElementById("saveFilesBtn");
  var picker = window.DiaryAttachments({
    onChange: function (files) {
      var live = recorder && (recorder.state === "recording" || recorder.state === "paused" || recorder.state === "uploading" || recorder.state === "processing");
      if (saveFilesBtn) {
        saveFilesBtn.disabled = files.length === 0 || live;
      }
    },
  });

  function showToast(message) {
    toast.hidden = false;
    toast.textContent = message;
  }

  function formatDuration(seconds) {
    var total = Math.floor(seconds);
    var minutes = String(Math.floor(total / 60)).padStart(2, "0");
    var secs = String(total % 60).padStart(2, "0");
    return minutes + ":" + secs;
  }

  var recorder = new VoiceDiaryRecorder({
    uploadUrl: config.uploadUrl,
    maxDuration: config.maxDuration,
    maxFileSize: config.maxFileSize,
  });

  recorder.onDurationUpdate = function (duration) {
    timer.textContent = formatDuration(duration);
  };
  recorder.onStateChange = function (state) {
    status.textContent = state;
    var live = state === "recording" || state === "paused";
    var busy = live || state === "uploading" || state === "processing";
    recordBtn.disabled = busy;
    pauseBtn.disabled = state !== "recording" && state !== "paused";
    pauseBtn.textContent = state === "paused" ? "Resume" : "Pause";
    stopBtn.disabled = !live;
    if (saveFilesBtn) {
      saveFilesBtn.disabled = picker.files().length === 0 || busy;
    }
  };
  recorder.onRollover = function () {
    showToast("Saved, continuing recording.");
  };
  recorder.onSegmentHeld = function () {
    showToast("Continuing. Everything will be saved as one recording.");
  };
  recorder.onInterruptionPause = function () {
    showToast("Recording paused. Resume when you are ready.");
  };
  recorder.onHeldPartsRecovered = function (count) {
    showToast("Recovered " + count + " saved part(s) from the last recording.");
  };
  recorder.onContentReady = function (data) {
    result.hidden = false;
    var line = data.content_text || "";
    if (data.route) {
      line += "\n" + data.route + " / " + data.intent + " / " + data.subject;
    }
    if (data.classification_error) {
      line += "\nClassification failed.";
    }
    if (data.attachment_count) {
      line += "\n" + data.attachment_count + " file(s) attached.";
    }
    result.textContent = line;
    picker.clear();
    status.textContent = "Saved";
  };
  recorder.onError = function (error) {
    status.textContent = error.message || "Recording failed";
  };

  recordBtn.addEventListener("click", function () {
    recorder.startRecording().catch(function (error) {
      status.textContent = error.message || "Could not start recording";
    });
  });
  pauseBtn.addEventListener("click", function () {
    if (recorder.state === "paused") {
      Promise.resolve(recorder.resumeRecording()).catch(function (error) {
        status.textContent = error.message || "Could not resume";
      });
    } else {
      recorder.pauseRecording();
    }
  });
  function saveStandaloneFiles() {
    var files = picker.files();
    if (!files.length) {
      return Promise.resolve();
    }
    var formData = new FormData();
    files.forEach(function (file) {
      formData.append("files", file);
    });
    if (saveFilesBtn) {
      saveFilesBtn.disabled = true;
    }
    return fetch(config.filesUploadUrl, {
      method: "POST",
      body: formData,
      headers: {
        "X-CSRFToken": recorder.getCsrfToken(),
        "Accept": "application/json",
      },
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          throw new Error(data.message || data.error || "Upload failed");
        }
        return data;
      });
    }).then(function (data) {
      result.hidden = false;
      result.textContent = (data.content_text || "Files saved") + "\n" + (data.attachment_count || files.length) + " file(s).";
      status.textContent = "Saved";
      picker.clear();
    }).catch(function (error) {
      status.textContent = error.message || "Could not save files";
      throw error;
    }).finally(function () {
      if (saveFilesBtn) {
        saveFilesBtn.disabled = picker.files().length === 0;
      }
    });
  }

  stopBtn.addEventListener("click", function () {
    recorder.stopRecording(picker.files()).then(function (outcome) {
      if (outcome && outcome.uploaded) {
        picker.clear();
        return;
      }
      if (picker.files().length) {
        return saveStandaloneFiles();
      }
    }).catch(function (error) {
      status.textContent = error.message || "Could not stop";
    });
  });
  if (saveFilesBtn) {
    saveFilesBtn.addEventListener("click", function () {
      saveStandaloneFiles().catch(function () {});
    });
  }

  recorder.recoverHeldParts().catch(function () {});
})();
