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

// Internationalization dictionaries (English, Simplified Chinese, Japanese, Spanish)
const I18N = {
  en: {
    pageTitle: "Blink Counter — Cross-Platform Eye Wellness Tracker",
    appTitle: "Blink Counter",
    appSubtitle: "Real-time webcam blink detector & eye-wellness companion",
    privacyBadge: "🔒 100% Local Processing",
    statusReady: "Ready",
    statusLoading: "Loading AI Model…",
    statusLive: "Live Tracking",
    statusPaused: "Paused",
    statusStopped: "Stopped",
    statusError: "Camera Error",
    statusDrowsy: "Drowsiness Alert",
    statusBreak: "Eye Break",
    statusLowBpm: "Low Blink Rate",
    statusDutySleep: "Camera Sleeping",
    placeholderTitle: "Start Camera to Track Blinks",
    placeholderDesc: "Runs completely inside your browser on macOS, Linux, and Windows using MediaPipe Face Landmarker. Video never leaves your device.",
    dutySleepTitle: "Duty-Cycle Camera Sleep (Saving Power)",
    dutySleepDesc: "Camera is completely powered off for {sec}s to save battery. Monitoring will resume automatically.",
    startCamera: "Start Camera",
    stopCamera: "Stop Camera",
    pause: "Pause",
    resume: "Resume",
    autoCalibrate: "Auto-Calibrate (3s)",
    resetSession: "Reset Session",
    exportCsv: "Export CSV",
    exportJson: "Export JSON",
    chartTitle: "Real-Time Eye Aspect Ratio (EAR)",
    legendEar: "Smoothed EAR",
    legendThreshold: "Blink Threshold",
    totalBlinks: "Total Blinks",
    waitingCamera: "Waiting for camera",
    noFace: "No face detected",
    eyesOpen: "Eyes open",
    eyesClosed: "Eyes closed",
    liveBlinkRate: "Live Blink Rate",
    healthyRange: "blinks / min (healthy: 15–20)",
    currentEar: "Current EAR",
    sessionTime: "Session Time",
    avgBpm: "Avg: {bpm} BPM",
    powerTitle: "⚡ Power Saver (Eco Mode)",
    powerHint: "Caps inference to 15 FPS, uses 480×270 video, and drops to 1.5 FPS when you step away.",
    idleBackoffLabel: "No-face idle backoff (1.5 FPS)",
    dutyCycleLabel: "Duty-cycle sampling (60s on / 240s camera off)",
    powerBadgeEco: "⚡ Eco · {fps} FPS",
    powerBadgeStd: "Standard · {fps} FPS",
    powerBadgeIdle: "💤 Idle · {fps} FPS",
    powerBadgeSleep: "🔋 Camera Off · {sec}s",
    breakTitle: "20-20-20 Eye Break Timer",
    breakHintDefault: "Every 20 min, look 20 ft (6 m) away for 20 sec.",
    breakPaused: "20-20-20 reminder paused.",
    breakLookAway: "Look 20 ft (6 m) away and relax your eyes!",
    breakCompleted: "Completed breaks: {count}",
    breakOff: "OFF",
    startBreakNow: "Start 20s Break",
    settingsTitle: "Detection & Alerts",
    earThresholdLabel: "EAR Threshold",
    lowBpmLabel: "Dry-Eye Alert Below (BPM)",
    drowsyLabel: "Drowsiness Closure (sec)",
    soundAlerts: "Sound alerts",
    eyeLandmarks: "Eye landmarks",
    mirrorVideo: "Mirror video",
    recentBlinks: "Recent Blinks",
    eventsCount: "{count} events",
    colTime: "Time",
    colDuration: "Duration",
    colMinEar: "Min EAR",
    noBlinksYet: "No blinks recorded yet.",
    footerLeft: "Blink Counter · Open-Source Cross-Platform Project (macOS, Linux & Windows)",
    footerRight: "Powered by MediaPipe Face Landmarker & Eye Aspect Ratio (EAR)",
    bannerCalibrating: "Calibrating open-eye baseline... look naturally at the screen ({pct}%)",
    bannerDrowsy: "DROWSINESS ALERT — Eyes closed for {sec}s!",
    bannerBreak: "20-20-20 EYE BREAK — Look 20 ft (6 m) away for {sec}s",
    bannerDryEye: "Low blink rate ({bpm} BPM) — Remember to blink to prevent dry eyes!",
    bannerCameraError: "Could not start camera or model: {err}",
  },
  zh: {
    pageTitle: "眨眼计数器 — 跨平台护眼健康助手",
    appTitle: "眨眼计数器",
    appSubtitle: "基于摄像头的实时眨眼监测与护眼健康助手",
    privacyBadge: "🔒 100% 本地处理",
    statusReady: "就绪",
    statusLoading: "正在加载 AI 模型…",
    statusLive: "实时监测中",
    statusPaused: "已暂停",
    statusStopped: "已停止",
    statusError: "摄像头错误",
    statusDrowsy: "疲劳预警",
    statusBreak: "护眼休息",
    statusLowBpm: "眨眼偏少",
    statusDutySleep: "摄像头休眠",
    placeholderTitle: "开启摄像头开始监测眨眼",
    placeholderDesc: "在 macOS、Linux 和 Windows 浏览器内 100% 本地运行（MediaPipe 人脸关键点），视频画面绝不上传。",
    dutySleepTitle: "省电采样休眠中（已关闭摄像头）",
    dutySleepDesc: "已完全释放摄像头传感器以节省电量，将在 {sec} 秒后自动恢复监测。",
    startCamera: "开启摄像头",
    stopCamera: "关闭摄像头",
    pause: "暂停",
    resume: "继续",
    autoCalibrate: "自动校准 (3秒)",
    resetSession: "重置会话",
    exportCsv: "导出 CSV",
    exportJson: "导出 JSON",
    chartTitle: "实时眼部纵横比 (EAR) 波形",
    legendEar: "平滑 EAR",
    legendThreshold: "眨眼阈值",
    totalBlinks: "累计眨眼次数",
    waitingCamera: "等待开启摄像头",
    noFace: "未检测到人脸",
    eyesOpen: "睁眼状态",
    eyesClosed: "闭眼状态",
    liveBlinkRate: "实时眨眼频率",
    healthyRange: "次/分钟（健康参考：15–20）",
    currentEar: "当前 EAR",
    sessionTime: "监测时长",
    avgBpm: "平均：{bpm} 次/分",
    powerTitle: "⚡ 省电模式 (Eco Mode)",
    powerHint: "推理限帧 15 FPS、低清 480×270 采集，离开座位时自动降至 1.5 FPS。",
    idleBackoffLabel: "无人脸自动降频 (1.5 FPS)",
    dutyCycleLabel: "间歇采样省电（开 60 秒 / 关摄像头 240 秒）",
    powerBadgeEco: "⚡ 省电 · {fps} FPS",
    powerBadgeStd: "标准 · {fps} FPS",
    powerBadgeIdle: "💤 待机 · {fps} FPS",
    powerBadgeSleep: "🔋 摄像头休眠 · {sec}秒",
    breakTitle: "20-20-20 护眼休息计时",
    breakHintDefault: "每用眼 20 分钟，远眺 6 米外景物 20 秒。",
    breakPaused: "20-20-20 提醒已关闭。",
    breakLookAway: "请远眺 6 米外景物，放松双眼！",
    breakCompleted: "已完成休息：{count} 次",
    breakOff: "已关闭",
    startBreakNow: "立即休息 20 秒",
    settingsTitle: "检测参数与提醒",
    earThresholdLabel: "EAR 判定阈值",
    lowBpmLabel: "眼干提醒阈值 (次/分)",
    drowsyLabel: "疲劳闭眼时长 (秒)",
    soundAlerts: "提示音",
    eyeLandmarks: "眼部关键点",
    mirrorVideo: "镜像画面",
    recentBlinks: "最近眨眼记录",
    eventsCount: "共 {count} 次",
    colTime: "时间",
    colDuration: "持续时长",
    colMinEar: "最小 EAR",
    noBlinksYet: "暂无眨眼记录。",
    footerLeft: "Blink Counter · 开源跨平台护眼项目（支持 macOS / Linux / Windows）",
    footerRight: "基于 MediaPipe Face Landmarker 与眼部纵横比 (EAR) 算法",
    bannerCalibrating: "正在校准睁眼基准值…请自然注视屏幕 ({pct}%)",
    bannerDrowsy: "疲劳预警 — 闭眼已持续 {sec} 秒！",
    bannerBreak: "20-20-20 护眼休息 — 请远眺 6 米外景物 {sec} 秒",
    bannerDryEye: "眨眼频率偏低 ({bpm} 次/分) — 记得多眨眼，预防眼干！",
    bannerCameraError: "无法启动摄像头或模型：{err}",
  },
  ja: {
    pageTitle: "まばたきカウンター — クロスプラットフォーム目の健康トラッカー",
    appTitle: "まばたきカウンター",
    appSubtitle: "リアルタイムWebカメラまばたき計測＆アイケアアシスタント",
    privacyBadge: "🔒 100% ローカル処理",
    statusReady: "準備完了",
    statusLoading: "AIモデル読込中…",
    statusLive: "計測中",
    statusPaused: "一時停止",
    statusStopped: "停止",
    statusError: "カメラエラー",
    statusDrowsy: "眠気警告",
    statusBreak: "目の休憩",
    statusLowBpm: "まばたき減少",
    statusDutySleep: "カメラスリープ",
    placeholderTitle: "カメラを開始してまばたきを計測",
    placeholderDesc: "macOS・Linux・Windowsのブラウザ内で完結動作（MediaPipe）。映像は外部へ送信されません。",
    dutySleepTitle: "省電力カメラスリープ中",
    dutySleepDesc: "バッテリー節約のためカメラを停止しています。{sec} 秒後に自動再開します。",
    startCamera: "カメラ開始",
    stopCamera: "カメラ停止",
    pause: "一時停止",
    resume: "再開",
    autoCalibrate: "自動校正 (3秒)",
    resetSession: "リセット",
    exportCsv: "CSV出力",
    exportJson: "JSON出力",
    chartTitle: "リアルタイム EAR（目の縦横比）波形",
    legendEar: "平滑化 EAR",
    legendThreshold: "しきい値",
    totalBlinks: "合計まばたき数",
    waitingCamera: "カメラ待機中",
    noFace: "顔が検出されません",
    eyesOpen: "開眼",
    eyesClosed: "閉眼",
    liveBlinkRate: "まばたき頻度",
    healthyRange: "回 / 分（目安：15–20）",
    currentEar: "現在の EAR",
    sessionTime: "計測時間",
    avgBpm: "平均: {bpm} BPM",
    powerTitle: "⚡ 省電力モード (Eco Mode)",
    powerHint: "推論を15 FPSに制限し、480×270映像と離席時の1.5 FPS待機で消費電力を削減。",
    idleBackoffLabel: "顔未検出時の自動省電力 (1.5 FPS)",
    dutyCycleLabel: "間欠サンプリング（60秒計測 / 240秒カメラOFF）",
    powerBadgeEco: "⚡ 省電力 · {fps} FPS",
    powerBadgeStd: "標準 · {fps} FPS",
    powerBadgeIdle: "💤 待機 · {fps} FPS",
    powerBadgeSleep: "🔋 カメラOFF · {sec}秒",
    breakTitle: "20-20-20 目の休憩タイマー",
    breakHintDefault: "20分ごとに6m先を20秒間眺めましょう。",
    breakPaused: "20-20-20 リマインダーOFF。",
    breakLookAway: "6m先を見て目を休めましょう！",
    breakCompleted: "完了した休憩: {count} 回",
    breakOff: "OFF",
    startBreakNow: "今すぐ20秒休憩",
    settingsTitle: "検出設定＆アラート",
    earThresholdLabel: "EAR しきい値",
    lowBpmLabel: "ドライアイ警告 (BPM以下)",
    drowsyLabel: "眠気判定の閉眼時間 (秒)",
    soundAlerts: "音声アラート",
    eyeLandmarks: "目のランドマーク",
    mirrorVideo: "左右反転",
    recentBlinks: "最近のまばたき",
    eventsCount: "{count} 件",
    colTime: "時刻",
    colDuration: "長さ",
    colMinEar: "最小 EAR",
    noBlinksYet: "まだ記録がありません。",
    footerLeft: "Blink Counter · オープンソース（macOS / Linux / Windows対応）",
    footerRight: "MediaPipe Face Landmarker & EAR アルゴリズム搭載",
    bannerCalibrating: "基準値を自動校正中…画面を自然に見てください ({pct}%)",
    bannerDrowsy: "眠気警告 — {sec} 秒間目が閉じています！",
    bannerBreak: "20-20-20 目の休憩 — 6m先を {sec} 秒間眺めてください",
    bannerDryEye: "まばたき減少 ({bpm} BPM) — ドライアイ予防のためまばたきを意識しましょう！",
    bannerCameraError: "カメラまたはモデルの起動に失敗しました: {err}",
  },
  es: {
    pageTitle: "Contador de Parpadeos — Salud Visual Multiplataforma",
    appTitle: "Contador de Parpadeos",
    appSubtitle: "Detector de parpadeos por cámara web y asistente de salud visual",
    privacyBadge: "🔒 100% Procesamiento Local",
    statusReady: "Listo",
    statusLoading: "Cargando modelo IA…",
    statusLive: "Rastreo Activo",
    statusPaused: "Pausado",
    statusStopped: "Detenido",
    statusError: "Error de Cámara",
    statusDrowsy: "Alerta de Somnolencia",
    statusBreak: "Pausa Visual",
    statusLowBpm: "Parpadeo Bajo",
    statusDutySleep: "Cámara en Reposo",
    placeholderTitle: "Inicia la Cámara para Contar Parpadeos",
    placeholderDesc: "Funciona localmente en tu navegador en macOS, Linux y Windows con MediaPipe. El video nunca sale de tu equipo.",
    dutySleepTitle: "Reposo de Cámara (Ahorro de Energía)",
    dutySleepDesc: "La cámara está completamente apagada por {sec}s para ahorrar batería. Se reanudará automáticamente.",
    startCamera: "Iniciar Cámara",
    stopCamera: "Detener Cámara",
    pause: "Pausar",
    resume: "Reanudar",
    autoCalibrate: "Autocalibrar (3s)",
    resetSession: "Reiniciar Sesión",
    exportCsv: "Exportar CSV",
    exportJson: "Exportar JSON",
    chartTitle: "Relación de Aspecto Ocular (EAR) en Tiempo Real",
    legendEar: "EAR Suavizado",
    legendThreshold: "Umbral",
    totalBlinks: "Total de Parpadeos",
    waitingCamera: "Esperando cámara",
    noFace: "Sin rostro detectado",
    eyesOpen: "Ojos abiertos",
    eyesClosed: "Ojos cerrados",
    liveBlinkRate: "Ritmo Actual",
    healthyRange: "parpadeos / min (normal: 15–20)",
    currentEar: "EAR Actual",
    sessionTime: "Duración",
    avgBpm: "Prom: {bpm} PPM",
    powerTitle: "⚡ Ahorro de Energía (Modo Eco)",
    powerHint: "Limita la inferencia a 15 FPS, usa video 480×270 y baja a 1.5 FPS si te alejas.",
    idleBackoffLabel: "Modo inactivo sin rostro (1.5 FPS)",
    dutyCycleLabel: "Muestreo cíclico (60s activa / 240s cámara apagada)",
    powerBadgeEco: "⚡ Eco · {fps} FPS",
    powerBadgeStd: "Estándar · {fps} FPS",
    powerBadgeIdle: "💤 Inactivo · {fps} FPS",
    powerBadgeSleep: "🔋 Cámara Off · {sec}s",
    breakTitle: "Temporizador 20-20-20",
    breakHintDefault: "Cada 20 min, mira a 6 metros de distancia por 20 seg.",
    breakPaused: "Recordatorio 20-20-20 desactivado.",
    breakLookAway: "¡Mira a 6 metros y descansa la vista!",
    breakCompleted: "Pausas completadas: {count}",
    breakOff: "OFF",
    startBreakNow: "Pausa de 20s",
    settingsTitle: "Detección y Alertas",
    earThresholdLabel: "Umbral EAR",
    lowBpmLabel: "Alerta de Ojo Seco (< PPM)",
    drowsyLabel: "Cierre por Somnolencia (seg)",
    soundAlerts: "Sonido",
    eyeLandmarks: "Puntos oculares",
    mirrorVideo: "Espejo",
    recentBlinks: "Parpadeos Recientes",
    eventsCount: "{count} eventos",
    colTime: "Hora",
    colDuration: "Duración",
    colMinEar: "EAR Mín",
    noBlinksYet: "Sin parpadeos registrados aún.",
    footerLeft: "Blink Counter · Proyecto Open-Source Multiplataforma (macOS, Linux y Windows)",
    footerRight: "Impulsado por MediaPipe Face Landmarker y EAR",
    bannerCalibrating: "Calibrando ojos abiertos... mire la pantalla naturalmente ({pct}%)",
    bannerDrowsy: "¡ALERTA DE SOMNOLENCIA — Ojos cerrados por {sec}s!",
    bannerBreak: "PAUSA 20-20-20 — Mire a 6 metros de distancia por {sec}s",
    bannerDryEye: "Ritmo de parpadeo bajo ({bpm} PPM) — ¡Recuerde parpadear para evitar ojos secos!",
    bannerCameraError: "No se pudo iniciar la cámara o el modelo: {err}",
  },
};

function detectInitialLang() {
  const params = new URLSearchParams(window.location.search);
  const queryLang = (params.get("lang") || "").toLowerCase().slice(0, 2);
  if (I18N[queryLang]) return queryLang;
  const saved = (localStorage.getItem("blink_counter_lang") || "").toLowerCase();
  if (I18N[saved]) return saved;
  const nav = (navigator.language || "en").toLowerCase().slice(0, 2);
  return I18N[nav] ? nav : "en";
}

let currentLang = detectInitialLang();

function t(key, vars = {}) {
  const dict = I18N[currentLang] || I18N.en;
  let str = dict[key] ?? I18N.en[key] ?? key;
  for (const [k, v] of Object.entries(vars)) {
    str = str.replaceAll(`{${k}}`, String(v));
  }
  return str;
}

// DOM references
const langSelect = document.getElementById("langSelect");
const powerBadge = document.getElementById("powerBadge");
const videoEl = document.getElementById("webcam");
const overlayCanvas = document.getElementById("overlayCanvas");
const overlayCtx = overlayCanvas.getContext("2d");
const videoWrapper = document.querySelector(".video-wrapper");
const placeholderEl = document.getElementById("cameraPlaceholder");
const placeholderTitle = document.getElementById("placeholderTitle");
const placeholderDesc = document.getElementById("placeholderDesc");
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

const ecoToggle = document.getElementById("ecoToggle");
const idleBackoffToggle = document.getElementById("idleBackoffToggle");
const dutyCycleToggle = document.getElementById("dutyCycleToggle");
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
let dutySleepTimerId = null;
let running = false;
let paused = false;
let inDutySleep = false;
let lastVideoTime = -1;
let audioCtx = null;

const DUTY_ON_MS = 60 * 1000;
const DUTY_OFF_MS = 240 * 1000;

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
  lastInferMs: 0,
  lastChartDrawMs: 0,
  lastFaceMs: null,
  dutyPhaseStartMs: null,
  maxBpm: 0,
  inBreak: false,
  nextBreakMs: null,
  breakEndMs: null,
};

function applyStaticTranslations() {
  document.documentElement.lang = currentLang;
  document.title = t("pageTitle");
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (key) el.textContent = t(key);
  });
  toggleCameraBtn.textContent = running ? t("stopCamera") : t("startCamera");
  pauseBtn.textContent = paused ? t("resume") : t("pause");
  logCountBadge.textContent = t("eventsCount", { count: state.blinkRecords.length });
  if (!running) {
    setStatusBadge(t("statusReady"), "pill-idle");
    eyeStateText.textContent = t("waitingCamera");
    avgBpmText.textContent = t("avgBpm", { bpm: "0.0" });
  }
  updatePowerBadge(performance.now());
}

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

function getEffectiveFps(nowMs) {
  const base = ecoToggle.checked ? 15 : 24;
  if (
    running &&
    idleBackoffToggle.checked &&
    state.lastFaceMs !== null &&
    nowMs - state.lastFaceMs >= 5000
  ) {
    return 1.5;
  }
  return base;
}

function updatePowerBadge(nowMs) {
  if (inDutySleep) {
    const rem = Math.max(0, Math.ceil((DUTY_OFF_MS - (nowMs - state.dutyPhaseStartMs)) / 1000));
    powerBadge.textContent = t("powerBadgeSleep", { sec: rem });
    powerBadge.className = "pill pill-eco";
    return;
  }
  const fps = getEffectiveFps(nowMs);
  if (fps <= 2) {
    powerBadge.textContent = t("powerBadgeIdle", { fps: fps.toFixed(1) });
    powerBadge.className = "pill pill-warn";
  } else if (ecoToggle.checked) {
    powerBadge.textContent = t("powerBadgeEco", { fps });
    powerBadge.className = "pill pill-eco";
  } else {
    powerBadge.textContent = t("powerBadgeStd", { fps });
    powerBadge.className = "pill pill-idle";
  }
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
  avgBpmText.textContent = t("avgBpm", { bpm: "0.0" });
  breakTimerValue.textContent = "20:00";
  logCountBadge.textContent = t("eventsCount", { count: 0 });
  blinkLogBody.innerHTML = `<tr><td colspan="4" class="empty-row">${t("noBlinksYet")}</td></tr>`;
  setBanner(null, "");
  drawEarChart();
}

function startCalibration() {
  state.calibrating = true;
  state.calibrationStartMs = performance.now();
  state.calibrationSamples = [];
  setBanner("info", t("bannerCalibrating", { pct: 0 }));
}

async function initFaceLandmarker() {
  if (faceLandmarker) return faceLandmarker;
  setStatusBadge(t("statusLoading"), "pill-warn");
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

async function openMediaStream() {
  const idealW = ecoToggle.checked ? 480 : 640;
  const idealH = ecoToggle.checked ? 270 : 360;
  const idealFps = ecoToggle.checked ? 15 : 24;
  mediaStream = await navigator.mediaDevices.getUserMedia({
    video: {
      width: { ideal: idealW },
      height: { ideal: idealH },
      frameRate: { ideal: idealFps, max: 30 },
      facingMode: "user",
    },
    audio: false,
  });
  videoEl.srcObject = mediaStream;
  await videoEl.play();
  overlayCanvas.width = videoEl.videoWidth || idealW;
  overlayCanvas.height = videoEl.videoHeight || idealH;
  lastVideoTime = -1;
}

function releaseMediaStream() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((tr) => tr.stop());
    mediaStream = null;
  }
  videoEl.srcObject = null;
  overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
}

function enterDutySleep() {
  inDutySleep = true;
  state.dutyPhaseStartMs = performance.now();
  if (rafId !== null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  releaseMediaStream();
  placeholderEl.classList.remove("hidden");
  startBtnPrimary.classList.add("hidden");
  setStatusBadge(t("statusDutySleep"), "pill-eco");

  const tickSleep = async () => {
    if (!running || !inDutySleep) return;
    const now = performance.now();
    const remMs = DUTY_OFF_MS - (now - state.dutyPhaseStartMs);
    if (!dutyCycleToggle.checked || remMs <= 0) {
      inDutySleep = false;
      startBtnPrimary.classList.remove("hidden");
      try {
        await openMediaStream();
        placeholderEl.classList.add("hidden");
        state.dutyPhaseStartMs = performance.now();
        state.lastFaceMs = performance.now();
        setStatusBadge(t("statusLive"), "pill-live");
        updatePowerBadge(performance.now());
        rafId = requestAnimationFrame(processFrame);
      } catch (err) {
        stopCamera();
        setBanner("danger", t("bannerCameraError", { err: err.message || err }));
      }
      return;
    }
    const remSec = Math.ceil(remMs / 1000);
    placeholderTitle.textContent = t("dutySleepTitle");
    placeholderDesc.textContent = t("dutySleepDesc", { sec: remSec });
    updatePowerBadge(now);
    dutySleepTimerId = setTimeout(tickSleep, 1000);
  };
  tickSleep();
}

async function startCamera() {
  try {
    toggleCameraBtn.disabled = true;
    startBtnPrimary.disabled = true;
    await initFaceLandmarker();
    await openMediaStream();

    placeholderEl.classList.add("hidden");
    startBtnPrimary.classList.remove("hidden");

    running = true;
    paused = false;
    inDutySleep = false;
    const now = performance.now();
    state.lastFaceMs = now;
    state.dutyPhaseStartMs = now;
    if (state.sessionStartMs === null) state.sessionStartMs = now;
    if (state.nextBreakMs === null) state.nextBreakMs = now + 20 * 60 * 1000;

    toggleCameraBtn.textContent = t("stopCamera");
    toggleCameraBtn.className = "btn btn-danger";
    toggleCameraBtn.disabled = false;
    pauseBtn.disabled = false;
    calibrateBtn.disabled = false;
    setStatusBadge(t("statusLive"), "pill-live");
    updatePowerBadge(now);

    startCalibration();
    rafId = requestAnimationFrame(processFrame);
  } catch (err) {
    console.error(err);
    setStatusBadge(t("statusError"), "pill-danger");
    setBanner("danger", t("bannerCameraError", { err: err.message || err }));
    toggleCameraBtn.disabled = false;
    startBtnPrimary.disabled = false;
  }
}

function stopCamera() {
  running = false;
  paused = false;
  inDutySleep = false;
  if (rafId !== null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  if (dutySleepTimerId !== null) {
    clearTimeout(dutySleepTimerId);
    dutySleepTimerId = null;
  }
  releaseMediaStream();
  placeholderTitle.textContent = t("placeholderTitle");
  placeholderDesc.textContent = t("placeholderDesc");
  startBtnPrimary.classList.remove("hidden");
  placeholderEl.classList.remove("hidden");

  toggleCameraBtn.textContent = t("startCamera");
  toggleCameraBtn.className = "btn btn-primary";
  startBtnPrimary.disabled = false;
  pauseBtn.textContent = t("pause");
  pauseBtn.disabled = true;
  calibrateBtn.disabled = true;
  setStatusBadge(t("statusStopped"), "pill-idle");
  setBanner(null, "");
  updatePowerBadge(performance.now());
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

  ctx.strokeStyle = "rgba(147, 164, 199, 0.12)";
  ctx.lineWidth = 1;
  for (const tick of [0.15, 0.25, 0.35]) {
    const y = toY(tick);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

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
  logCountBadge.textContent = t("eventsCount", { count: state.blinkRecords.length });
}

function updateBreakTimer(nowMs) {
  if (!breakToggle.checked) {
    breakTimerValue.textContent = t("breakOff");
    breakHint.textContent = t("breakPaused");
    return null;
  }

  if (state.inBreak) {
    const remSec = Math.max(0, (state.breakEndMs - nowMs) / 1000);
    breakTimerValue.textContent = `${Math.ceil(remSec)}s`;
    breakHint.textContent = t("breakLookAway");
    if (remSec <= 0) {
      state.inBreak = false;
      state.breaksCompleted += 1;
      state.nextBreakMs = nowMs + 20 * 60 * 1000;
      playTone("gentle");
      return null;
    }
    return t("bannerBreak", { sec: Math.ceil(remSec) });
  }

  if (state.nextBreakMs === null) state.nextBreakMs = nowMs + 20 * 60 * 1000;
  const untilSec = Math.max(0, (state.nextBreakMs - nowMs) / 1000);
  breakTimerValue.textContent = formatDuration(untilSec);
  breakHint.textContent = t("breakCompleted", { count: state.breaksCompleted });
  if (untilSec <= 0) {
    state.inBreak = true;
    state.breakEndMs = nowMs + 20 * 1000;
    playTone("gentle");
    return t("bannerBreak", { sec: 20 });
  }
  return null;
}

function processFrame(nowMs) {
  if (!running || inDutySleep) return;
  rafId = requestAnimationFrame(processFrame);

  if (paused || videoEl.readyState < 2) return;

  // Check duty-cycle camera off transition
  if (dutyCycleToggle.checked && state.dutyPhaseStartMs !== null && nowMs - state.dutyPhaseStartMs >= DUTY_ON_MS) {
    enterDutySleep();
    return;
  }

  // FPS pacing (15 FPS Eco / 24 FPS Standard / 1.5 FPS Idle Backoff)
  const targetFps = getEffectiveFps(nowMs);
  const minIntervalMs = 1000 / targetFps;
  if (nowMs - state.lastInferMs < minIntervalMs) return;
  if (videoEl.currentTime === lastVideoTime) return;

  state.lastInferMs = nowMs;
  lastVideoTime = videoEl.currentTime;
  updatePowerBadge(nowMs);

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
    eyeStateText.textContent = t("noFace");
  } else {
    state.lastFaceMs = nowMs;
    const lm = result.faceLandmarks[0];
    const left = computeEar(lm, LEFT_EYE, width, height);
    const right = computeEar(lm, RIGHT_EYE, width, height);
    const rawEar = (left.ear + right.ear) / 2;

    state.smoothedEar =
      state.smoothedEar === null
        ? rawEar
        : state.smoothingAlpha * rawEar + (1 - state.smoothingAlpha) * state.smoothedEar;

    if (state.calibrating) {
      if (rawEar > 0.1) state.calibrationSamples.push(rawEar);
      const calElapsed = (nowMs - state.calibrationStartMs) / 1000;
      const pct = Math.min(100, Math.round((calElapsed / 3.0) * 100));
      setBanner("info", t("bannerCalibrating", { pct }));
      if (calElapsed >= 3.0 && state.calibrationSamples.length >= 8) {
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
    eyeStateText.textContent = state.eyesClosed ? t("eyesClosed") : t("eyesOpen");

    state.earHistory.push({ ear: state.smoothedEar, blink: blinkThisFrame });
    if (state.earHistory.length > 140) state.earHistory.shift();

    // Throttle chart redraws in Eco mode (~6 Hz) to minimize canvas GPU repaints
    const chartInterval = ecoToggle.checked ? 160 : 50;
    if (blinkThisFrame || nowMs - state.lastChartDrawMs >= chartInterval) {
      state.lastChartDrawMs = nowMs;
      drawEarChart();
    }
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
  avgBpmText.textContent = t("avgBpm", { bpm: avgBpm.toFixed(1) });

  const breakMsg = updateBreakTimer(nowMs);
  const lowBpmLimit = parseFloat(lowBpmSlider.value);
  const dryEyeWarn = elapsedSec >= 30 && currentBpm < lowBpmLimit;
  if (dryEyeWarn && (state.lastDryEyeAlertMs === null || nowMs - state.lastDryEyeAlertMs >= 45000)) {
    state.lastDryEyeAlertMs = nowMs;
    state.dryEyeAlerts += 1;
    playTone("gentle");
  }

  if (!state.calibrating) {
    if (drowsyNow) {
      setStatusBadge(t("statusDrowsy"), "pill-danger");
      setBanner("danger", t("bannerDrowsy", { sec: (closureMs / 1000).toFixed(1) }));
    } else if (breakMsg) {
      setStatusBadge(t("statusBreak"), "pill-warn");
      setBanner("break", breakMsg);
    } else if (dryEyeWarn) {
      setStatusBadge(t("statusLowBpm"), "pill-warn");
      setBanner("warn", t("bannerDryEye", { bpm: currentBpm.toFixed(1) }));
    } else {
      setStatusBadge(t("statusLive"), "pill-live");
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
    language: currentLang,
    eco_mode: ecoToggle.checked,
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
langSelect.value = currentLang;
langSelect.addEventListener("change", (e) => {
  currentLang = e.target.value;
  localStorage.setItem("blink_counter_lang", currentLang);
  applyStaticTranslations();
});

ecoToggle.addEventListener("change", () => updatePowerBadge(performance.now()));
idleBackoffToggle.addEventListener("change", () => updatePowerBadge(performance.now()));
dutyCycleToggle.addEventListener("change", () => {
  state.dutyPhaseStartMs = performance.now();
  updatePowerBadge(performance.now());
});

toggleCameraBtn.addEventListener("click", () => (running ? stopCamera() : startCamera()));
startBtnPrimary.addEventListener("click", startCamera);
pauseBtn.addEventListener("click", () => {
  paused = !paused;
  pauseBtn.textContent = paused ? t("resume") : t("pause");
  setStatusBadge(paused ? t("statusPaused") : t("statusLive"), paused ? "pill-warn" : "pill-live");
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

// Initialize UI
videoWrapper.classList.add("mirrored");
applyStaticTranslations();
drawEarChart();
