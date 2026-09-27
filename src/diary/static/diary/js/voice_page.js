(function () {
  var config = JSON.parse(document.getElementById("recorder-config").textContent);
  var timer = document.getElementById("timer");
  var status = document.getElementById("status");
  var toast = document.getElementById("toast");
  var result = document.getElementById("result");
  var recordBtn = document.getElementById("recordBtn");
  var pauseBtn = document.getElementById("pauseBtn");
  var stopBtn = document.getElementById("stopBtn");

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
    recordBtn.disabled = live || state === "uploading" || state === "processing";
    pauseBtn.disabled = state !== "recording" && state !== "paused";
    pauseBtn.textContent = state === "paused" ? "Resume" : "Pause";
    stopBtn.disabled = !live;
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
    result.textContent = line;
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
  stopBtn.addEventListener("click", function () {
    recorder.stopRecording().catch(function (error) {
      status.textContent = error.message || "Could not stop";
    });
  });

  recorder.recoverHeldParts().catch(function () {});
})();
