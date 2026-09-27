(function () {
  var config = JSON.parse(document.getElementById("recorder-config").textContent);
  var timer = document.getElementById("timer");
  var status = document.getElementById("status");
  var toast = document.getElementById("toast");
  var result = document.getElementById("result");
  var recordBtn = document.getElementById("recordBtn");
  var pauseBtn = document.getElementById("pauseBtn");
  var stopBtn = document.getElementById("stopBtn");
  var session = { id: null, sequence: 1 };

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
    status.textContent = state;
    var live = state === "recording" || state === "paused";
    var busy = live || state === "uploading" || state === "processing";
    recordBtn.disabled = busy;
    pauseBtn.disabled = state !== "recording" && state !== "paused";
    pauseBtn.textContent = state === "paused" ? "Resume" : "Pause";
    stopBtn.disabled = !live;
  };
  recorder.onRollover = function () {
    showToast("Segment saved. Continuing.");
  };
  recorder.onContentReady = function (data) {
    result.hidden = false;
    result.textContent = data.content_text || "";
    if (data.transcription_error) {
      result.textContent += "\nTranscription failed.";
    }
    status.textContent = data.status === "complete" ? "Saved" : status.textContent;
    clearSession();
  };
  recorder.onError = function (error) {
    status.textContent = error.message || "Recording failed";
  };

  recordBtn.addEventListener("click", function () {
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
      status.textContent = error.message || "Could not start conference";
      if (id) {
        postForm(config.stopUrl, { conference_id: id }).catch(function () {});
      }
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
      result.hidden = false;
      result.textContent = data.content_text || "";
      status.textContent = "Saved";
      clearSession();
    }).catch(function (error) {
      status.textContent = error.message || "Could not stop";
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
      result.hidden = false;
      result.textContent = data.content_text || "";
      status.textContent = "Saved";
    }).catch(function () {
      status.textContent = "Could not recover the conference";
    }).finally(function () {
      clearSession();
    });
  }
})();
