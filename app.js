import {
  FaceLandmarker,
  FilesetResolver,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";

// Canonical MediaPipe 6-point eye landmark indices for EAR calculation
const LEFT_EYE = [33, 160, 158, 133, 153, 144];
const RIGHT_EYE = [362, 385, 387, 263, 373, 380];

const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const WASM_ROOT =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm";

// DOM references
const videoEl = document.getElementById("webcam");
const overlayCanvas = document.getElementById("overlayCanvas");
const overlayCtx = overlayCanvas.getContext("2d");
const videoWrapper = document.querySelector(".video-wrapper");
const placeholderEl = document.getElementById("cameraPlaceholder");
const earChartCanvas = document.getElementById("earChart");
const earChartCtx = earChartCanvas.getContext("2d");

const statusBadge = document.getElementById("statusBadge");
const alertBanner = document.getElementById("alertBanner");
const toggleCameraBtn = document.getElementById("toggleCameraBtn");
const startBtnPrimary = document.getElementById("startBtnPrimary");
const pauseBtn = document.getElementById("pauseBtn");
const calibrateBtn = document.getElementById("calibrateBtn");
const resetBtn = document.getElementById("resetBtn");
const exportCsvBtn = document.getElementById("exportCsvBtn");
const exportJsonBtn = document.getElementById("exportJsonBtn");
const takeBreakNowBtn = document.getElementById("takeBreakNowBtn");

const totalBlinksValue = document.getElementById("totalBlinksValue");
const eyeStateText = document.getElementById("eyeStateText");
const bpmValue = document.getElementById("bpmValue");
const earValue = document.getElementById("earValue");
const perclosText = document.getElementById("perclosText");
const sessionTimeValue = document.getElementById("sessionTimeValue");
const avgBpmText = document.getElementById("avgBpmText");
const breakTimerValue = document.getElementById("breakTimerValue");
const breakHint = document.getElementById("breakHint");
const blinkLogBody = document.getElementById("blinkLogBody");
const logCountBadge = document.getElementById("logCountBadge");

const thresholdSlider = document.getElementById("thresholdSlider");
const thresholdReadout = document.getElementById("thresholdReadout");
const legendThreshold = document.getElementById("legendThreshold");
const lowBpmSlider = document.getElementById("lowBpmSlider");
const lowBpmReadout = document.getElementById("lowBpmReadout");
const drowsySlider = document.getElementById("drowsySlider");
const drowsyReadout = document.getElementById("drowsyReadout");
const soundToggle = document.getElementById("soundToggle");
const overlayToggle = document.getElementById("overlayToggle");
const mirrorToggle = document.getElementById("mirrorToggle");
const breakToggle = document.getElementById("breakToggle");

// Runtime state
let faceLandmarker = null;
let mediaStream = null;
let rafId = null;
let running = false;
let paused = false;
let lastVideoTime = -1;
let audioCtx = null;

const state = {
  sessionStartMs: null,
  totalBlinks: 0,
  drowsyEvents: 0,
  dryEyeAlerts: 0,
  breaksCompleted: 0,
  earThreshold: 0.21,
  hysteresis: 0.02,
  smoothingAlpha: 0.45,
  smoothedEar: null,
  eyesClosed: false,
  closedFrames: 0,
  closureStartMs: null,
  closureMinEar: 1.0,
  lastBlinkMs: null,
  drowsyTriggeredForClosure: false,
  lastDryEyeAlertMs: null,
  calibrating: false,
  calibrationStartMs: null,
  calibrationSamples: [],
  blinkTimestamps: [],
  blinkRecords: [],
  earHistory: [],
  perclosSamples: [],
  lastFrameMs: null,
  maxBpm: 0,
  inBreak: false,
  nextBreakMs: null,
  breakEndMs: null,
};

function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function computeEar(landmarks, indices, width, height) {
  const pts = indices.map((i) => ({
    x: landmarks[i].x * width,
    y: landmarks[i].y * height,
  }));
  const horiz = dist(pts[0], pts[3]);
  if (horiz <= 1e-6) return { ear: 0, pts };
  const v1 = dist(pts[1], pts[5]);
  const v2 = dist(pts[2], pts[4]);
  return { ear: (v1 + v2) / (2 * horiz), pts };
}

function formatDuration(sec) {
  const total = Math.max(0, Math.floor(sec));
  const m = Math.floor(total / 60);
  const s = total % 60;
  const h = Math.floor(m / 60);
  if (h > 0) {
    return `${String(h).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function playTone(type = "gentle") {
  if (!soundToggle.checked) return;
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === "suspended") audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type === "drowsy" ? "triangle" : "sine";
    osc.frequency.setValueAtTime(type === "drowsy" ? 880 : 620, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.001, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.12, audioCtx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + (type === "drowsy" ? 0.35 : 0.18));
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + (type === "drowsy" ? 0.38 : 0.2));
  } catch {
    // AudioContext may be blocked until user interaction
  }
}

function setBanner(kind, message) {
  if (!message) {
    alertBanner.className = "alert-banner hidden";
    alertBanner.textContent = "";
    return;
  }
  alertBanner.className = `alert-banner ${kind}`;
  alertBanner.textContent = message;
}

function setStatusBadge(label, cls) {
  statusBadge.textContent = label;
  statusBadge.className = `pill ${cls}`;
}

function updateThresholdUI(val) {
  state.earThreshold = val;
  thresholdSlider.value = val.toFixed(3);
  thresholdReadout.textContent = val.toFixed(2);
  legendThreshold.textContent = val.toFixed(2);
}

function resetSession(keepCalibration = true) {
  const now = performance.now();
  state.sessionStartMs = running ? now : null;
  state.totalBlinks = 0;
  state.drowsyEvents = 0;
  state.dryEyeAlerts = 0;
  state.breaksCompleted = 0;
  state.smoothedEar = null;
  state.eyesClosed = false;
  state.closedFrames = 0;
  state.closureStartMs = null;
  state.closureMinEar = 1.0;
  state.lastBlinkMs = null;
  state.drowsyTriggeredForClosure = false;
  state.lastDryEyeAlertMs = null;
  state.blinkTimestamps = [];
  state.blinkRecords = [];
  state.earHistory = [];
  state.perclosSamples = [];
  state.lastFrameMs = null;
  state.maxBpm = 0;
  state.inBreak = false;
  state.breakEndMs = null;
  state.nextBreakMs = running ? now + 20 * 60 * 1000 : null;
  if (!keepCalibration) {
    state.calibrating = false;
    state.calibrationSamples = [];
  }

  totalBlinksValue.textContent = "0";
  bpmValue.textContent = "0.0";
  earValue.textContent = "0.000";
  perclosText.textContent = "PERCLOS: 0.0%";
  sessionTimeValue.textContent = "00:00";
  avgBpmText.textContent = "Avg: 0.0 BPM";
  breakTimerValue.textContent = "20:00";
  logCountBadge.textContent = "0 events";
  blinkLogBody.innerHTML = '<tr><td colspan="4" class="empty-row">No blinks recorded yet.</td></tr>';
  setBanner(null, "");
  drawEarChart();
}

function startCalibration() {
  state.calibrating = true;
  state.calibrationStartMs = performance.now();
  state.calibrationSamples = [];
  setBanner("info", "Calibrating open-eye baseline... Look naturally at your screen for 3 seconds.");
}

async function initFaceLandmarker() {
  if (faceLandmarker) return faceLandmarker;
  setStatusBadge("Loading AI Model…", "pill-warn");
  const filesetResolver = await FilesetResolver.forVisionTasks(WASM_ROOT);
  faceLandmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
    baseOptions: {
      modelAssetPath: MODEL_URL,
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numFaces: 1,
    minFaceDetectionConfidence: 0.5,
    minFacePresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
  return faceLandmarker;
}

async function startCamera() {
  try {
    toggleCameraBtn.disabled = true;
    startBtnPrimary.disabled = true;
    await initFaceLandmarker();

    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 960 }, height: { ideal: 540 }, facingMode: "user" },
      audio: false,
    });
    videoEl.srcObject = mediaStream;
    await videoEl.play();

    overlayCanvas.width = videoEl.videoWidth || 960;
    overlayCanvas.height = videoEl.videoHeight || 540;
    placeholderEl.classList.add("hidden");

    running = true;
    paused = false;
    const now = performance.now();
    if (state.sessionStartMs === null) state.sessionStartMs = now;
    if (state.nextBreakMs === null) state.nextBreakMs = now + 20 * 60 * 1000;

    toggleCameraBtn.textContent = "Stop Camera";
    toggleCameraBtn.className = "btn btn-danger";
    toggleCameraBtn.disabled = false;
    pauseBtn.disabled = false;
    calibrateBtn.disabled = false;
    setStatusBadge("Live Tracking", "pill-live");

    startCalibration();
    rafId = requestAnimationFrame(processFrame);
  } catch (err) {
    console.error(err);
    setStatusBadge("Camera Error", "pill-danger");
    setBanner("danger", `Could not start camera or model: ${err.message || err}`);
    toggleCameraBtn.disabled = false;
    startBtnPrimary.disabled = false;
  }
}

function stopCamera() {
  running = false;
  paused = false;
  if (rafId !== null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  videoEl.srcObject = null;
  overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  placeholderEl.classList.remove("hidden");

  toggleCameraBtn.textContent = "Start Camera";
  toggleCameraBtn.className = "btn btn-primary";
  startBtnPrimary.disabled = false;
  pauseBtn.textContent = "Pause";
  pauseBtn.disabled = true;
  calibrateBtn.disabled = true;
  setStatusBadge("Stopped", "pill-idle");
  setBanner(null, "");
}

function drawEyeOverlay(leftPts, rightPts, closed) {
  overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  if (!overlayToggle.checked || !leftPts || !rightPts) return;

  const color = closed ? "#f87171" : "#34d399";
  overlayCtx.strokeStyle = color;
  overlayCtx.lineWidth = 2.2;
  overlayCtx.fillStyle = "#ffffff";

  for (const pts of [leftPts, rightPts]) {
    overlayCtx.beginPath();
    pts.forEach((p, idx) => {
      if (idx === 0) overlayCtx.moveTo(p.x, p.y);
      else overlayCtx.lineTo(p.x, p.y);
    });
    overlayCtx.closePath();
    overlayCtx.stroke();

    for (const p of pts) {
      overlayCtx.beginPath();
      overlayCtx.arc(p.x, p.y, 2.5, 0, Math.PI * 2);
      overlayCtx.fill();
    }
  }
}

function drawEarChart() {
  const ctx = earChartCtx;
  const w = earChartCanvas.width;
  const h = earChartCanvas.height;
  ctx.clearRect(0, 0, w, h);

  const minEar = 0.08;
  const maxEar = 0.42;
  const toY = (v) => {
    const norm = Math.max(0, Math.min(1, (v - minEar) / (maxEar - minEar)));
    return h - 14 - norm * (h - 28);
  };

  // Horizontal subtle grid lines
  ctx.strokeStyle = "rgba(147, 164, 199, 0.12)";
  ctx.lineWidth = 1;
  for (const tick of [0.15, 0.25, 0.35]) {
    const y = toY(tick);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // Threshold dashed line
  const ty = toY(state.earThreshold);
  ctx.save();
  ctx.strokeStyle = "#fbbf24";
  ctx.setLineDash([6, 5]);
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(0, ty);
  ctx.lineTo(w, ty);
  ctx.stroke();
  ctx.restore();

  if (state.earHistory.length < 2) return;

  // EAR waveform curve
  ctx.strokeStyle = "#34d399";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  const n = state.earHistory.length;
  state.earHistory.forEach((sample, idx) => {
    const x = (idx / Math.max(1, n - 1)) * w;
    const y = toY(sample.ear);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Mark blink peaks
  ctx.fillStyle = "#38bdf8";
  state.earHistory.forEach((sample, idx) => {
    if (sample.blink) {
      const x = (idx / Math.max(1, n - 1)) * w;
      const y = toY(sample.ear);
      ctx.beginPath();
      ctx.arc(x, y, 4.5, 0, Math.PI * 2);
      ctx.fill();
    }
  });
}

function appendBlinkRow(rec) {
  if (state.blinkRecords.length === 1) {
    blinkLogBody.innerHTML = "";
  }
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>#${rec.blink_index}</td>
    <td>${rec.clock_time}</td>
    <td>${rec.duration_ms.toFixed(0)} ms</td>
    <td>${rec.min_ear.toFixed(3)}</td>
  `;
  blinkLogBody.prepend(tr);
  while (blinkLogBody.children.length > 40) {
    blinkLogBody.removeChild(blinkLogBody.lastChild);
  }
  logCountBadge.textContent = `${state.blinkRecords.length} events`;
}

function updateBreakTimer(nowMs) {
  if (!breakToggle.checked) {
    breakTimerValue.textContent = "OFF";
    breakHint.textContent = "20-20-20 reminder paused.";
    return null;
  }

  if (state.inBreak) {
    const remSec = Math.max(0, (state.breakEndMs - nowMs) / 1000);
    breakTimerValue.textContent = `${Math.ceil(remSec)}s`;
    breakHint.textContent = "Look 20 ft (6 m) away and relax your eyes!";
    if (remSec <= 0) {
      state.inBreak = false;
      state.breaksCompleted += 1;
      state.nextBreakMs = nowMs + 20 * 60 * 1000;
      playTone("gentle");
      return null;
    }
    return `20-20-20 EYE BREAK — Look 20 ft (6 m) away for ${Math.ceil(remSec)}s`;
  }

  if (state.nextBreakMs === null) state.nextBreakMs = nowMs + 20 * 60 * 1000;
  const untilSec = Math.max(0, (state.nextBreakMs - nowMs) / 1000);
  breakTimerValue.textContent = formatDuration(untilSec);
  breakHint.textContent = `Completed breaks: ${state.breaksCompleted}`;
  if (untilSec <= 0) {
    state.inBreak = true;
    state.breakEndMs = nowMs + 20 * 1000;
    playTone("gentle");
    return "20-20-20 EYE BREAK — Look 20 ft (6 m) away for 20s";
  }
  return null;
}

function processFrame(nowMs) {
  if (!running) return;
  rafId = requestAnimationFrame(processFrame);

  if (paused || videoEl.readyState < 2) return;
  if (videoEl.currentTime === lastVideoTime) return;
  lastVideoTime = videoEl.currentTime;

  const width = videoEl.videoWidth;
  const height = videoEl.videoHeight;
  if (overlayCanvas.width !== width || overlayCanvas.height !== height) {
    overlayCanvas.width = width;
    overlayCanvas.height = height;
  }

  const dtSec = state.lastFrameMs === null ? 0 : Math.min(1, Math.max(0, (nowMs - state.lastFrameMs) / 1000));
  state.lastFrameMs = nowMs;

  const result = faceLandmarker.detectForVideo(videoEl, nowMs);
  let blinkThisFrame = false;
  let drowsyNow = false;
  let closureMs = 0;

  if (!result.faceLandmarks || result.faceLandmarks.length === 0) {
    overlayCtx.clearRect(0, 0, width, height);
    state.eyesClosed = false;
    state.closedFrames = 0;
    state.closureStartMs = null;
    eyeStateText.textContent = "No face detected";
  } else {
    const lm = result.faceLandmarks[0];
    const left = computeEar(lm, LEFT_EYE, width, height);
    const right = computeEar(lm, RIGHT_EYE, width, height);
    const rawEar = (left.ear + right.ear) / 2;

    state.smoothedEar =
      state.smoothedEar === null
        ? rawEar
        : state.smoothingAlpha * rawEar + (1 - state.smoothingAlpha) * state.smoothedEar;

    // Auto-calibration (3 seconds)
    if (state.calibrating) {
      if (rawEar > 0.1) state.calibrationSamples.push(rawEar);
      const calElapsed = (nowMs - state.calibrationStartMs) / 1000;
      const pct = Math.min(100, Math.round((calElapsed / 3.0) * 100));
      setBanner("info", `Calibrating open-eye baseline... look naturally at the screen (${pct}%)`);
      if (calElapsed >= 3.0 && state.calibrationSamples.length >= 10) {
        const sorted = [...state.calibrationSamples].sort((a, b) => a - b);
        const baseline = sorted[Math.floor(sorted.length * 0.75)];
        const adaptive = Math.max(0.14, Math.min(0.28, baseline * 0.72));
        updateThresholdUI(adaptive);
        state.calibrating = false;
        setBanner(null, "");
      }
    }

    const closeThr = state.earThreshold;
    const openThr = state.earThreshold + state.hysteresis;
    const drowsyLimitMs = parseFloat(drowsySlider.value) * 1000;

    if (!state.eyesClosed) {
      if (state.smoothedEar < closeThr) {
        state.eyesClosed = true;
        state.closedFrames = 1;
        state.closureStartMs = nowMs;
        state.closureMinEar = state.smoothedEar;
        state.drowsyTriggeredForClosure = false;
      }
    } else {
      state.closureMinEar = Math.min(state.closureMinEar, state.smoothedEar);
      if (state.smoothedEar >= openThr) {
        const durMs = Math.max(0, nowMs - state.closureStartMs);
        const cooldownOk = state.lastBlinkMs === null || nowMs - state.lastBlinkMs >= 140;
        if (!state.calibrating && state.closedFrames >= 2 && durMs >= 50 && durMs <= 800 && cooldownOk) {
          state.totalBlinks += 1;
          state.lastBlinkMs = nowMs;
          state.blinkTimestamps.push(nowMs);
          blinkThisFrame = true;

          const rec = {
            blink_index: state.totalBlinks,
            iso_time: new Date().toISOString(),
            clock_time: new Date().toLocaleTimeString(),
            elapsed_sec: Number(((nowMs - state.sessionStartMs) / 1000).toFixed(2)),
            duration_ms: Number(durMs.toFixed(1)),
            min_ear: Number(state.closureMinEar.toFixed(4)),
            left_ear: Number(left.ear.toFixed(4)),
            right_ear: Number(right.ear.toFixed(4)),
          };
          state.blinkRecords.push(rec);
          appendBlinkRow(rec);
        }
        state.eyesClosed = false;
        state.closedFrames = 0;
        state.closureStartMs = null;
        state.drowsyTriggeredForClosure = false;
      } else {
        state.closedFrames += 1;
        closureMs = Math.max(0, nowMs - state.closureStartMs);
        if (!state.calibrating && closureMs >= drowsyLimitMs) {
          drowsyNow = true;
          if (!state.drowsyTriggeredForClosure) {
            state.drowsyTriggeredForClosure = true;
            state.drowsyEvents += 1;
            playTone("drowsy");
          }
        }
      }
    }

    drawEyeOverlay(left.pts, right.pts, state.eyesClosed);
    earValue.textContent = state.smoothedEar.toFixed(3);
    eyeStateText.textContent = state.eyesClosed ? "Eyes closed" : "Eyes open";

    state.earHistory.push({ ear: state.smoothedEar, blink: blinkThisFrame });
    if (state.earHistory.length > 150) state.earHistory.shift();
    drawEarChart();
  }

  // Rolling PERCLOS (60s)
  if (dtSec > 0) {
    state.perclosSamples.push({ t: nowMs, dt: dtSec, closed: state.eyesClosed });
  }
  const perclosCutoff = nowMs - 60000;
  while (state.perclosSamples.length && state.perclosSamples[0].t < perclosCutoff) {
    state.perclosSamples.shift();
  }
  const totalDt = state.perclosSamples.reduce((acc, s) => acc + s.dt, 0);
  const closedDt = state.perclosSamples.reduce((acc, s) => acc + (s.closed ? s.dt : 0), 0);
  const perclos = totalDt > 0 ? (closedDt / totalDt) * 100 : 0;
  perclosText.textContent = `PERCLOS: ${perclos.toFixed(1)}%`;

  // Session time & rolling BPM
  const elapsedSec = Math.max(0, (nowMs - state.sessionStartMs) / 1000);
  const bpmCutoff = nowMs - 60000;
  while (state.blinkTimestamps.length && state.blinkTimestamps[0] < bpmCutoff) {
    state.blinkTimestamps.shift();
  }
  const effWindow = Math.min(60, Math.max(elapsedSec, 1));
  const currentBpm = elapsedSec < 5 ? 0 : (state.blinkTimestamps.length / effWindow) * 60;
  const avgBpm = elapsedSec < 5 ? 0 : (state.totalBlinks / elapsedSec) * 60;
  if (currentBpm > state.maxBpm) state.maxBpm = currentBpm;

  totalBlinksValue.textContent = String(state.totalBlinks);
  bpmValue.textContent = currentBpm.toFixed(1);
  sessionTimeValue.textContent = formatDuration(elapsedSec);
  avgBpmText.textContent = `Avg: ${avgBpm.toFixed(1)} BPM`;

  const breakMsg = updateBreakTimer(nowMs);
  const lowBpmLimit = parseFloat(lowBpmSlider.value);
  const dryEyeWarn = elapsedSec >= 30 && currentBpm < lowBpmLimit;
  if (dryEyeWarn && (state.lastDryEyeAlertMs === null || nowMs - state.lastDryEyeAlertMs >= 45000)) {
    state.lastDryEyeAlertMs = nowMs;
    state.dryEyeAlerts += 1;
    playTone("gentle");
  }

  // Banner priority: calibration > drowsiness > 20-20-20 break > dry-eye
  if (!state.calibrating) {
    if (drowsyNow) {
      setStatusBadge("Drowsiness Alert", "pill-danger");
      setBanner("danger", `DROWSINESS ALERT — Eyes closed for ${(closureMs / 1000).toFixed(1)}s!`);
    } else if (breakMsg) {
      setStatusBadge("Eye Break", "pill-warn");
      setBanner("break", breakMsg);
    } else if (dryEyeWarn) {
      setStatusBadge("Low Blink Rate", "pill-warn");
      setBanner("warn", `Low blink rate (${currentBpm.toFixed(1)} BPM) — Remember to blink to prevent dry eyes!`);
    } else {
      setStatusBadge("Live Tracking", "pill-live");
      setBanner(null, "");
    }
  }
}

function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportCsv() {
  const header = ["blink_index", "iso_time", "elapsed_sec", "duration_ms", "min_ear", "left_ear", "right_ear"];
  const rows = state.blinkRecords.map((r) => header.map((k) => r[k]).join(","));
  const csv = [header.join(","), ...rows].join("\n");
  downloadFile(`blink-counter-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`, csv, "text/csv");
}

function exportJson() {
  const elapsedSec = state.sessionStartMs ? (performance.now() - state.sessionStartMs) / 1000 : 0;
  const payload = {
    exported_at: new Date().toISOString(),
    metrics: {
      total_blinks: state.totalBlinks,
      duration_sec: Number(elapsedSec.toFixed(2)),
      avg_bpm: elapsedSec >= 5 ? Number(((state.totalBlinks / elapsedSec) * 60).toFixed(1)) : 0,
      max_bpm: Number(state.maxBpm.toFixed(1)),
      drowsy_events: state.drowsyEvents,
      dry_eye_alerts: state.dryEyeAlerts,
      breaks_completed: state.breaksCompleted,
      ear_threshold: Number(state.earThreshold.toFixed(4)),
    },
    blinks: state.blinkRecords,
  };
  downloadFile(
    `blink-counter-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`,
    JSON.stringify(payload, null, 2),
    "application/json"
  );
}

// Event bindings
toggleCameraBtn.addEventListener("click", () => (running ? stopCamera() : startCamera()));
startBtnPrimary.addEventListener("click", startCamera);
pauseBtn.addEventListener("click", () => {
  paused = !paused;
  pauseBtn.textContent = paused ? "Resume" : "Pause";
  setStatusBadge(paused ? "Paused" : "Live Tracking", paused ? "pill-warn" : "pill-live");
});
calibrateBtn.addEventListener("click", startCalibration);
resetBtn.addEventListener("click", () => resetSession(true));
exportCsvBtn.addEventListener("click", exportCsv);
exportJsonBtn.addEventListener("click", exportJson);
takeBreakNowBtn.addEventListener("click", () => {
  const now = performance.now();
  state.inBreak = true;
  state.breakEndMs = now + 20 * 1000;
  playTone("gentle");
});

thresholdSlider.addEventListener("input", (e) => {
  state.calibrating = false;
  updateThresholdUI(parseFloat(e.target.value));
  drawEarChart();
});
lowBpmSlider.addEventListener("input", (e) => {
  lowBpmReadout.textContent = e.target.value;
});
drowsySlider.addEventListener("input", (e) => {
  drowsyReadout.textContent = `${parseFloat(e.target.value).toFixed(1)}s`;
});
mirrorToggle.addEventListener("change", () => {
  videoWrapper.classList.toggle("mirrored", mirrorToggle.checked);
});

// Initialize default mirrored view and empty chart
videoWrapper.classList.add("mirrored");
drawEarChart();
