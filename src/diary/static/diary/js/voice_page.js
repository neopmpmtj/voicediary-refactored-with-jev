(function () {
  var config = JSON.parse(document.getElementById("recorder-config").textContent);
  var timer = document.getElementById("timer");
  var status = document.getElementById("status");
  var result = document.getElementById("result");
  var placeholder = document.getElementById("transcriptionPlaceholder");
  var recordBtn = document.getElementById("recordBtn");
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

  function formatDuration(seconds) {
    var total = Math.floor(seconds);
    var minutes = String(Math.floor(total / 60)).padStart(2, "0");
    var secs = String(total % 60).padStart(2, "0");
    return minutes + ":" + secs;
  }

  function showResult(text) {
    if (placeholder) {
      placeholder.classList.add("hidden");
    }
    result.classList.remove("hidden");
    result.textContent = text;
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
    if (status) {
      status.textContent = state === "uploading" ? "Uploading..." : "Processing...";
    }
    window.VDUI.applyRecordState(state, { recordBtn: recordBtn, stopBtn: stopBtn });
    var busy = state === "recording" || state === "paused" || state === "uploading" || state === "processing";
    if (saveFilesBtn) {
      saveFilesBtn.disabled = picker.files().length === 0 || busy;
    }
  };
  recorder.onRollover = function () {
    window.VDUI.showToast("Saved, continuing recording.");
  };
  recorder.onSegmentHeld = function () {
    window.VDUI.showToast("Continuing. Everything will be saved as one recording.");
  };
  recorder.onInterruptionPause = function () {
    window.VDUI.showToast("Recording paused. Resume when you are ready.");
  };
  recorder.onHeldPartsRecovered = function (count) {
    window.VDUI.showToast("Recovered " + count + " saved part(s) from the last recording.");
  };
  recorder.onContentReady = function (data) {
    var line = data.content_text || "";
    if (data.route) {
      line += "\n" + data.route + " / " + data.intent + " / " + data.subject;
    }
    if (data.classification_error) {
      line += "\nClassification failed.";
    }
    if (data.bookings && data.bookings.length) {
      data.bookings.forEach(function (booking) {
        var part = booking.summary || "calendar";
        line += "\n" + part + " " + booking.status;
        if (booking.problem) {
          line += ": " + booking.problem;
        }
      });
    }
    if (data.finance && data.finance.length) {
      data.finance.forEach(function (record) {
        var part = record.record_name || "finance";
        line += "\n" + part + " " + record.status;
        if (record.error_message) {
          line += ": " + record.error_message;
        } else if (record.items && record.items.length) {
          record.items.forEach(function (item) {
            line += " " + item.type + " " + item.amount + " " + item.currency;
          });
        }
      });
    }
    if (data.attachment_count) {
      line += "\n" + data.attachment_count + " file(s) attached.";
    }
    showResult(line);
    picker.clear();
  };
  recorder.onError = function (error) {
    window.VDUI.showToast(error.message || "Recording failed", "error");
  };

  recordBtn.addEventListener("click", function () {
    if (recorder.state === "recording") {
      recorder.pauseRecording();
      return;
    }
    if (recorder.state === "paused") {
      Promise.resolve(recorder.resumeRecording()).catch(function (error) {
        window.VDUI.showToast(error.message || "Could not resume", "error");
      });
      return;
    }
    recorder.startRecording().catch(function (error) {
      window.VDUI.showToast(error.message || "Could not start recording", "error");
    });
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
      showResult((data.content_text || "Files saved") + "\n" + (data.attachment_count || files.length) + " file(s).");
      picker.clear();
    }).catch(function (error) {
      window.VDUI.showToast(error.message || "Could not save files", "error");
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
      window.VDUI.showToast(error.message || "Could not stop", "error");
    });
  });
  if (saveFilesBtn) {
    saveFilesBtn.addEventListener("click", function () {
      saveStandaloneFiles().catch(function () {});
    });
  }

  recorder.recoverHeldParts().catch(function () {});
})();
