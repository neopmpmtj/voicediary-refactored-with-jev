(function () {
  var config = JSON.parse(document.getElementById("recorder-config").textContent);
  var timer = document.getElementById("timer");
  var status = document.getElementById("status");
  var result = document.getElementById("result");
  var placeholder = document.getElementById("resultPlaceholder");
  var recordBtn = document.getElementById("recordBtn");
  var stopBtn = document.getElementById("stopBtn");
  var session = { id: null, sequence: 1 };

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

  function postForm(url, fields) {
    var body = new FormData();
    Object.keys(fields).forEach(function (key) {
      body.append(key, fields[key]);
    });
    return fetch(url, {
      method: "POST",
      body: body,
      headers: {
        "X-CSRFToken": recorder.getCsrfToken(),
        "Accept": "application/json",
      },
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          throw new Error(data.message || data.error || "Request failed");
        }
        return data;
      });
    });
  }

  var recorder = new VoiceDiaryRecorder({
    uploadUrl: config.segmentUrl,
    maxDuration: config.maxDuration,
    maxFileSize: config.maxFileSize,
  });
  recorder.backupOwner = "conference";

  function rememberSession() {
    if (!session.id) {
      sessionStorage.removeItem("vdConferenceId");
      sessionStorage.removeItem("vdConferenceSequence");
      return;
    }
    sessionStorage.setItem("vdConferenceId", session.id);
    sessionStorage.setItem("vdConferenceSequence", String(session.sequence));
  }

  function clearSession() {
    session.id = null;
    session.sequence = 1;
    rememberSession();
  }

  recorder.appendUploadFields = function (formData, options) {
    if (!session.id) {
      throw new Error("Conference has not started");
    }
    formData.append("conference_id", session.id);
    formData.append("sequence", String(session.sequence));
    session.sequence += 1;
    formData.append("final", options.background ? "0" : "1");
    rememberSession();
  };

  recorder.onDurationUpdate = function (duration) {
    timer.textContent = formatDuration(duration);
  };
  recorder.onStateChange = function (state) {
    if (status) {
      status.textContent = state === "uploading" ? "Uploading..." : "Processing...";
    }
    window.VDUI.applyRecordState(state, { recordBtn: recordBtn, stopBtn: stopBtn });
  };
  recorder.onRollover = function () {
    window.VDUI.showToast("Segment saved. Continuing.");
  };
  recorder.onContentReady = function (data) {
    var text = data.content_text || "";
    if (data.transcription_error) {
      text += "\nTranscription failed.";
    }
    showResult(text);
    clearSession();
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
    recordBtn.disabled = true;
    postForm(config.startUrl, {}).then(function (data) {
      session.id = data.conference_id;
      session.sequence = 1;
      rememberSession();
      return recorder.startRecording();
    }).catch(function (error) {
      var id = session.id;
      clearSession();
      recordBtn.disabled = false;
      window.VDUI.showToast(error.message || "Could not start conference", "error");
      if (id) {
        postForm(config.stopUrl, { conference_id: id }).catch(function () {});
      }
    });
  });
  stopBtn.addEventListener("click", function () {
    var id = session.id;
    var sequenceBefore = session.sequence;
    recorder.stopRecording().then(function () {
      if (!id || session.sequence !== sequenceBefore) {
        return null;
      }
      return postForm(config.stopUrl, { conference_id: id });
    }).then(function (data) {
      if (!data) {
        return;
      }
      showResult(data.content_text || "");
      clearSession();
    }).catch(function (error) {
      window.VDUI.showToast(error.message || "Could not stop", "error");
    });
  });

  var savedId = sessionStorage.getItem("vdConferenceId");
  var savedSequence = parseInt(sessionStorage.getItem("vdConferenceSequence") || "1", 10);
  if (savedId) {
    session.id = savedId;
    session.sequence = savedSequence > 0 ? savedSequence : 1;
    recorder.recoverHeldParts().then(function () {
      return postForm(config.stopUrl, { conference_id: savedId });
    }).then(function (data) {
      if (!data) {
        return;
      }
      showResult(data.content_text || "");
    }).catch(function () {
      window.VDUI.showToast("Could not recover the conference", "error");
    }).finally(function () {
      clearSession();
    });
  }
})();
