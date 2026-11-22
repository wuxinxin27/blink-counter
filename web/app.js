// Offline-first MediaPipe Tasks Vision loader (uses bundled ./vendor/ in Tauri Desktop App, falls back to CDN on Web)
const LOCAL_VISION_MODULE = "./vendor/mediapipe/vision_bundle.mjs";
const LOCAL_WASM_ROOT = "./vendor/mediapipe/wasm";
const LOCAL_MODEL_URL = "./vendor/models/face_landmarker.task";

const CDN_VISION_MODULE =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";
const CDN_WASM_ROOT =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm";
const CDN_MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";

// Tauri v2 Desktop bridge (null when running in a standard browser / PWA)
const tauriCore = window.__TAURI__?.core || null;
const tauriEvent = window.__TAURI__?.event || null;
const isTauriDesktop = Boolean(tauriCore);

// Internal 6-point eye landmark indices used under the hood for blink detection
const LEFT_EYE = [33, 160, 158, 133, 153, 144];
const RIGHT_EYE = [362, 385, 387, 263, 373, 380];

// Sensitivity presets map friendly labels to internal detection ratios
const SENSITIVITY_MAP = {
  low: { ratio: 0.66, defaultThreshold: 0.19 },
  standard: { ratio: 0.72, defaultThreshold: 0.21 },
  high: { ratio: 0.78, defaultThreshold: 0.235 },
};

// Internationalization dictionaries (English, Simplified Chinese, Japanese, Spanish)
const I18N = {
  en: {
    pageTitle: "Blink Counter — Cross-Platform Eye Wellness Tracker",
    appTitle: "Blink Counter",
    appSubtitle: "Real-time blink frequency & eye-wellness tracker",
    installApp: "⬇ Install App",
    minimizeTray: "📥 Hide to Tray",
    trayTooltip: "Blink Counter · {bpm} BPM · {blinks} blinks",
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
    placeholderTitle: "Start Camera to Track Blink Frequency",
    placeholderDesc: "Runs 100% locally inside your browser on macOS, Linux, and Windows. Video never leaves your device.",
    dutySleepTitle: "Duty-Cycle Camera Sleep (Saving Power)",
    dutySleepDesc: "Camera is completely powered off for {sec}s to save battery. Monitoring will resume automatically.",
    startCamera: "Start Camera",
    stopCamera: "Stop Camera",
    pause: "Pause",
    resume: "Resume",
    autoCalibrate: "Recalibrate",
    resetSession: "Reset Session",
    exportCsv: "Export CSV",
    exportJson: "Export JSON",
    chartTitle: "Blink Frequency Trend (Blinks / Min)",
    legendBpm: "Blink Rate",
    legendHealthy: "Healthy (15–20)",
    legendAlert: "Alert (<",
    liveBlinkRate: "Live Blink Rate",
    healthyRange: "blinks / min (healthy: 15–20)",
    rateHealthy: "Healthy blink frequency",
    rateLow: "Low — remember to blink!",
    rateWarmup: "Measuring blink frequency…",
    totalBlinks: "Total Blinks",
    waitingCamera: "Waiting for camera",
    noFace: "No face detected",
    eyesOpen: "Eyes open",
    eyesClosed: "Eyes closed",
    avgBlinkRate: "Average Rate",
    peakBpm: "Peak: {bpm} BPM",
    sessionTime: "Session Time",
    breaksSummary: "Breaks taken: {count}",
    powerTitle: "⚡ Power Saver (Eco Mode)",
    powerHint: "Caps inference to 15 FPS, stops all rendering when minimized, and drops to 1.5 FPS when away.",
    hideVideoLabel: "Hide video preview (save GPU & battery)",
    videoHiddenTitle: "Video Preview Off (Ultra-Low Battery)",
    videoHiddenDesc: "Video and canvas rendering are paused to save GPU & battery while blink frequency tracking continues.",
    showVideo: "Show Video Preview",
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
    settingsTitle: "Blink Alerts & Preferences",
    lowBpmLabel: "Dry-Eye Alert Below (BPM)",
    drowsyLabel: "Drowsiness Closure (sec)",
    sensitivityLabel: "Blink Sensitivity",
    sensLow: "Low",
    sensStandard: "Standard",
    sensHigh: "High",
    soundAlerts: "Sound alerts",
    autostartLabel: "Launch at login",
    popupAlerts: "Pop-up & system alerts",
    testAlert: "🔔 Test Pop-up & Sound",
    modalDismiss: "Got it",
    popupDryEyeTitle: "Blink Reminder — Low Blink Rate",
    popupDryEyeBody: "Your blink rate dropped to {bpm} blinks/min (healthy: 15–20). Please blink gently a few times to keep your eyes moist.",
    popupBreakTitle: "20-20-20 Eye Break — Look Far Away",
    popupBreakBody: "Time to relax your eyes! Look at something 20 ft (6 m) away for 20 seconds.",
    popupBreakDoneTitle: "Eye Break Complete",
    popupBreakDoneBody: "Great job! Your 20-second far-gaze break is complete.",
    popupDrowsyTitle: "Drowsiness Alert",
    popupDrowsyBody: "Your eyes have been closed for {sec}s. Take a brief rest if you feel tired.",
    eyeLandmarks: "Eye tracking lines",
    mirrorVideo: "Mirror video",
    recentBlinks: "Recent Blinks",
    eventsCount: "{count} blinks",
    colTime: "Time",
    colDuration: "Duration",
    colRate: "Blink Rate",
    noBlinksYet: "No blinks recorded yet.",
    footerLeft: "Blink Counter · Open-Source Cross-Platform Project (macOS, Linux & Windows)",
    footerRight: "100% Free & Local Blink Frequency & Eye-Wellness Tracking",
    bannerCalibrating: "Calibrating automatically... look naturally at the screen ({pct}%)",
    bannerDrowsy: "DROWSINESS ALERT — Eyes closed for {sec}s!",
    bannerBreak: "20-20-20 EYE BREAK — Look 20 ft (6 m) away for {sec}s",
    bannerDryEye: "Low blink rate ({bpm} BPM) — Remember to blink to prevent dry eyes!",
    bannerCameraError: "Could not start camera or model: {err}",
    bpmUnit: "{bpm} BPM",
  },
  zh: {
    pageTitle: "眨眼计数器 — 跨平台护眼频率监测助手",
    appTitle: "眨眼计数器",
    appSubtitle: "实时眨眼频率监测与护眼健康助手",
    installApp: "⬇ 安装到本地",
    minimizeTray: "📥 隐藏到托盘",
    trayTooltip: "眨眼计数器 · {bpm} 次/分 · 累计 {blinks} 次",
    privacyBadge: "🔒 100% 本地处理",
    statusReady: "就绪",
    statusLoading: "正在加载模型…",
    statusLive: "实时监测中",
    statusPaused: "已暂停",
    statusStopped: "已停止",
    statusError: "摄像头错误",
    statusDrowsy: "疲劳预警",
    statusBreak: "护眼休息",
    statusLowBpm: "眨眼偏少",
    statusDutySleep: "摄像头休眠",
    placeholderTitle: "开启摄像头开始监测眨眼频率",
    placeholderDesc: "在 macOS、Linux 和 Windows 浏览器内 100% 本地运行，视频画面绝不上传。",
    dutySleepTitle: "省电采样休眠中（已关闭摄像头）",
    dutySleepDesc: "已完全关闭摄像头以节省电量，将在 {sec} 秒后自动恢复监测。",
    startCamera: "开启摄像头",
    stopCamera: "关闭摄像头",
    pause: "暂停",
    resume: "继续",
    autoCalibrate: "重新校准",
    resetSession: "重置会话",
    exportCsv: "导出 CSV",
    exportJson: "导出 JSON",
    chartTitle: "眨眼频率趋势（次/分钟）",
    legendBpm: "实时频率",
    legendHealthy: "健康区间 (15–20)",
    legendAlert: "偏低提醒 (<",
    liveBlinkRate: "实时眨眼频率",
    healthyRange: "次/分钟（健康参考：15–20）",
    rateHealthy: "眨眼频率健康",
    rateLow: "频率偏低，记得多眨眼！",
    rateWarmup: "正在计算眨眼频率…",
    totalBlinks: "累计眨眼次数",
    waitingCamera: "等待开启摄像头",
    noFace: "未检测到人脸",
    eyesOpen: "睁眼",
    eyesClosed: "闭眼",
    avgBlinkRate: "平均眨眼频率",
    peakBpm: "峰值：{bpm} 次/分",
    sessionTime: "监测时长",
    breaksSummary: "已完成休息：{count} 次",
    powerTitle: "⚡ 省电模式 (Eco Mode)",
    powerHint: "限帧 15 FPS、最小化时自动停止渲染，离开座位自动降至 1.5 FPS。",
    hideVideoLabel: "隐藏视频画面（极致省电，不渲染视频）",
    videoHiddenTitle: "已关闭视频预览（极致省电中）",
    videoHiddenDesc: "已停止视频画面与画布渲染以大幅降低耗电，后台仍在持续监测眨眼频率并触发提醒。",
    showVideo: "恢复视频预览",
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
    settingsTitle: "提醒与灵敏度设置",
    lowBpmLabel: "眼干提醒阈值（次/分）",
    drowsyLabel: "疲劳闭眼时长（秒）",
    sensitivityLabel: "眨眼检测灵敏度",
    sensLow: "低",
    sensStandard: "标准",
    sensHigh: "高",
    soundAlerts: "提示音",
    autostartLabel: "开机自启动",
    popupAlerts: "弹窗与系统通知提醒",
    testAlert: "🔔 测试弹窗与音效",
    modalDismiss: "知道了",
    popupDryEyeTitle: "护眼提醒：眨眼频率过低",
    popupDryEyeBody: "当前眨眼频率仅 {bpm} 次/分（健康参考 15–20 次/分）。请有意识地轻轻多眨几次眼，缓解眼干疲劳。",
    popupBreakTitle: "远眺护眼提醒 (20-20-20)",
    popupBreakBody: "已连续用眼一段时间，请将视线移开屏幕，远眺 6 米外景物 20 秒放松双眼。",
    popupBreakDoneTitle: "远眺休息完成",
    popupBreakDoneBody: "已完成 20 秒远眺放松，现在可以继续使用电脑了。",
    popupDrowsyTitle: "疲劳闭眼预警",
    popupDrowsyBody: "检测到您已连续闭眼 {sec} 秒，如感到困倦请适当休息。",
    eyeLandmarks: "眼部轮廓线",
    mirrorVideo: "镜像画面",
    recentBlinks: "最近眨眼记录",
    eventsCount: "共 {count} 次",
    colTime: "时间",
    colDuration: "持续时长",
    colRate: "当时频率",
    noBlinksYet: "暂无眨眼记录。",
    footerLeft: "Blink Counter · 开源跨平台护眼项目（支持 macOS / Linux / Windows）",
    footerRight: "100% 免费本地运行的眨眼频率与护眼助手",
    bannerCalibrating: "正在自动校准…请自然注视屏幕 ({pct}%)",
    bannerDrowsy: "疲劳预警 — 闭眼已持续 {sec} 秒！",
    bannerBreak: "20-20-20 护眼休息 — 请远眺 6 米外景物 {sec} 秒",
    bannerDryEye: "眨眼频率偏低 ({bpm} 次/分) — 记得多眨眼，预防眼干！",
    bannerCameraError: "无法启动摄像头或模型：{err}",
    bpmUnit: "{bpm} 次/分",
  },
  ja: {
    pageTitle: "まばたきカウンター — 目の健康トラッカー",
    appTitle: "まばたきカウンター",
    appSubtitle: "リアルタイムまばたき頻度＆アイケアアシスタント",
    installApp: "⬇ アプリをインストール",
    minimizeTray: "📥 トレイへ最小化",
    trayTooltip: "まばたきカウンター · {bpm} 回/分 · 計 {blinks} 回",
    privacyBadge: "🔒 100% ローカル処理",
    statusReady: "準備完了",
    statusLoading: "モデル読込中…",
    statusLive: "計測中",
    statusPaused: "一時停止",
    statusStopped: "停止",
    statusError: "カメラエラー",
    statusDrowsy: "眠気警告",
    statusBreak: "目の休憩",
    statusLowBpm: "まばたき減少",
    statusDutySleep: "カメラスリープ",
    placeholderTitle: "カメラを開始してまばたき頻度を計測",
    placeholderDesc: "macOS・Linux・Windowsのブラウザ内で100%ローカル動作。映像は外部送信されません。",
    dutySleepTitle: "省電力カメラスリープ中",
    dutySleepDesc: "バッテリー節約のためカメラを停止しています。{sec} 秒後に自動再開します。",
    startCamera: "カメラ開始",
    stopCamera: "カメラ停止",
    pause: "一時停止",
    resume: "再開",
    autoCalibrate: "再調整",
    resetSession: "リセット",
    exportCsv: "CSV出力",
    exportJson: "JSON出力",
    chartTitle: "まばたき頻度の推移（回 / 分）",
    legendBpm: "まばたき頻度",
    legendHealthy: "健康目安 (15–20)",
    legendAlert: "警告 (<",
    liveBlinkRate: "現在のまばたき頻度",
    healthyRange: "回 / 分（健康目安：15–20）",
    rateHealthy: "健康的なペースです",
    rateLow: "減少中 — 意識してまばたきを！",
    rateWarmup: "頻度を計測しています…",
    totalBlinks: "合計まばたき数",
    waitingCamera: "カメラ待機中",
    noFace: "顔が検出されません",
    eyesOpen: "開眼",
    eyesClosed: "閉眼",
    avgBlinkRate: "平均頻度",
    peakBpm: "最大: {bpm} 回/分",
    sessionTime: "計測時間",
    breaksSummary: "休憩回数: {count} 回",
    powerTitle: "⚡ 省電力モード (Eco Mode)",
    powerHint: "15 FPS制限・最小化時の描画自動停止・離席時1.5 FPS待機でバッテリー消費を最小化。",
    hideVideoLabel: "映像プレビューを非表示（超省電力）",
    videoHiddenTitle: "映像プレビューOFF（超省電力モード）",
    videoHiddenDesc: "GPUとバッテリー節約のため映像描画を停止中です。まばたき頻度の計測とアラートは継続しています。",
    showVideo: "映像を再表示",
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
    settingsTitle: "アラート＆感度設定",
    lowBpmLabel: "ドライアイ警告（回/分以下）",
    drowsyLabel: "眠気判定の閉眼時間（秒）",
    sensitivityLabel: "検出感度",
    sensLow: "低",
    sensStandard: "標準",
    sensHigh: "高",
    soundAlerts: "音声アラート",
    autostartLabel: "ログイン時に自動起動",
    popupAlerts: "ポップアップ＆システム通知",
    testAlert: "🔔 ポップアップ＆音テスト",
    modalDismiss: "OK",
    popupDryEyeTitle: "まばたきリマインダー（頻度低下）",
    popupDryEyeBody: "現在のまばたき頻度は {bpm} 回/分です（目安 15–20）。ドライアイ予防のためゆっくり数回まばたきしましょう。",
    popupBreakTitle: "20-20-20 遠くを見る休憩",
    popupBreakBody: "目を休める時間です。画面から目を離し、6m先を20秒間眺めてください。",
    popupBreakDoneTitle: "目の休憩が完了しました",
    popupBreakDoneBody: "20秒間の遠方休憩が完了しました。",
    popupDrowsyTitle: "眠気警告",
    popupDrowsyBody: "{sec} 秒間目が閉じています。疲れている場合は少し休憩してください。",
    eyeLandmarks: "目のトラッキング線",
    mirrorVideo: "左右反転",
    recentBlinks: "最近のまばたき",
    eventsCount: "{count} 回",
    colTime: "時刻",
    colDuration: "長さ",
    colRate: "頻度",
    noBlinksYet: "まだ記録がありません。",
    footerLeft: "Blink Counter · オープンソース（macOS / Linux / Windows対応）",
    footerRight: "完全無料・ローカル動作のまばたき頻度トラッカー",
    bannerCalibrating: "自動調整中…画面を自然に見てください ({pct}%)",
    bannerDrowsy: "眠気警告 — {sec} 秒間目が閉じています！",
    bannerBreak: "20-20-20 目の休憩 — 6m先を {sec} 秒間眺めてください",
    bannerDryEye: "まばたき減少 ({bpm} 回/分) — ドライアイ予防のためまばたきを意識しましょう！",
    bannerCameraError: "カメラまたはモデルの起動に失敗しました: {err}",
    bpmUnit: "{bpm} 回/分",
  },
  es: {
    pageTitle: "Contador de Parpadeos — Salud Visual Multiplataforma",
    appTitle: "Contador de Parpadeos",
    appSubtitle: "Monitor de frecuencia de parpadeo y salud visual en tiempo real",
    installApp: "⬇ Instalar App",
    minimizeTray: "📥 Ocultar en Bandeja",
    trayTooltip: "Contador de Parpadeos · {bpm} PPM · {blinks} parpadeos",
    privacyBadge: "🔒 100% Procesamiento Local",
    statusReady: "Listo",
    statusLoading: "Cargando modelo…",
    statusLive: "Rastreo Activo",
    statusPaused: "Pausado",
    statusStopped: "Detenido",
    statusError: "Error de Cámara",
    statusDrowsy: "Alerta de Somnolencia",
    statusBreak: "Pausa Visual",
    statusLowBpm: "Parpadeo Bajo",
    statusDutySleep: "Cámara en Reposo",
    placeholderTitle: "Inicia la Cámara para Medir tu Frecuencia",
    placeholderDesc: "Funciona 100% localmente en tu navegador en macOS, Linux y Windows. El video nunca sale de tu equipo.",
    dutySleepTitle: "Reposo de Cámara (Ahorro de Energía)",
    dutySleepDesc: "La cámara está completamente apagada por {sec}s para ahorrar batería. Se reanudará automáticamente.",
    startCamera: "Iniciar Cámara",
    stopCamera: "Detener Cámara",
    pause: "Pausar",
    resume: "Reanudar",
    autoCalibrate: "Recalibrar",
    resetSession: "Reiniciar Sesión",
    exportCsv: "Exportar CSV",
    exportJson: "Exportar JSON",
    chartTitle: "Tendencia de Frecuencia de Parpadeo (PPM)",
    legendBpm: "Ritmo",
    legendHealthy: "Saludable (15–20)",
    legendAlert: "Alerta (<",
    liveBlinkRate: "Frecuencia Actual",
    healthyRange: "parpadeos / min (normal: 15–20)",
    rateHealthy: "Frecuencia saludable",
    rateLow: "Baja — ¡recuerda parpadear!",
    rateWarmup: "Calculando frecuencia…",
    totalBlinks: "Total de Parpadeos",
    waitingCamera: "Esperando cámara",
    noFace: "Sin rostro detectado",
    eyesOpen: "Ojos abiertos",
    eyesClosed: "Ojos cerrados",
    avgBlinkRate: "Ritmo Promedio",
    peakBpm: "Máximo: {bpm} PPM",
    sessionTime: "Duración",
    breaksSummary: "Pausas: {count}",
    powerTitle: "⚡ Ahorro de Energía (Modo Eco)",
    powerHint: "Limita a 15 FPS, detiene el renderizado al minimizar y baja a 1.5 FPS si te alejas.",
    hideVideoLabel: "Ocultar vista previa de video (ahorro máximo)",
    videoHiddenTitle: "Vista Previa Desactivada (Ahorro Máximo)",
    videoHiddenDesc: "El renderizado de video y gráficos está pausado para ahorrar batería mientras sigue el monitoreo.",
    showVideo: "Mostrar Video",
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
    settingsTitle: "Alertas y Preferencias",
    lowBpmLabel: "Alerta de Ojo Seco (< PPM)",
    drowsyLabel: "Cierre por Somnolencia (seg)",
    sensitivityLabel: "Sensibilidad",
    sensLow: "Baja",
    sensStandard: "Estándar",
    sensHigh: "Alta",
    soundAlerts: "Sonido",
    autostartLabel: "Iniciar al encender",
    popupAlerts: "Ventanas emergentes y notificaciones",
    testAlert: "🔔 Probar Aviso y Sonido",
    modalDismiss: "Entendido",
    popupDryEyeTitle: "Recordatorio: Parpadeo Bajo",
    popupDryEyeBody: "Tu frecuencia bajó a {bpm} parpadeos/min (normal: 15–20). Parpadea suavemente varias veces para lubricar tus ojos.",
    popupBreakTitle: "Pausa 20-20-20 — Mira a lo Lejos",
    popupBreakBody: "Relaja tu vista: mira un punto a 6 metros de distancia durante 20 segundos.",
    popupBreakDoneTitle: "Pausa Visual Completada",
    popupBreakDoneBody: "¡Excelente! Terminaron los 20 segundos de descanso visual.",
    popupDrowsyTitle: "Alerta de Somnolencia",
    popupDrowsyBody: "Tus ojos llevan cerrados {sec}s. Toma un descanso breve si tienes sueño.",
    eyeLandmarks: "Líneas oculares",
    mirrorVideo: "Espejo",
    recentBlinks: "Parpadeos Recientes",
    eventsCount: "{count} parpadeos",
    colTime: "Hora",
    colDuration: "Duración",
    colRate: "Frecuencia",
    noBlinksYet: "Sin parpadeos registrados aún.",
    footerLeft: "Blink Counter · Proyecto Open-Source Multiplataforma (macOS, Linux y Windows)",
    footerRight: "Seguimiento 100% gratuito y local de frecuencia de parpadeo",
    bannerCalibrating: "Calibrando automáticamente... mire la pantalla naturalmente ({pct}%)",
    bannerDrowsy: "¡ALERTA DE SOMNOLENCIA — Ojos cerrados por {sec}s!",
    bannerBreak: "PAUSA 20-20-20 — Mire a 6 metros de distancia por {sec}s",
    bannerDryEye: "Ritmo de parpadeo bajo ({bpm} PPM) — ¡Recuerde parpadear para evitar ojos secos!",
    bannerCameraError: "No se pudo iniciar la cámara o el modelo: {err}",
    bpmUnit: "{bpm} PPM",
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
const bpmChartCanvas = document.getElementById("bpmChart");
const bpmChartCtx = bpmChartCanvas.getContext("2d");

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

const bpmValue = document.getElementById("bpmValue");
const rateHealthText = document.getElementById("rateHealthText");
const totalBlinksValue = document.getElementById("totalBlinksValue");
const eyeStateText = document.getElementById("eyeStateText");
const avgBpmValue = document.getElementById("avgBpmValue");
const peakBpmText = document.getElementById("peakBpmText");
const sessionTimeValue = document.getElementById("sessionTimeValue");
const breaksSummaryText = document.getElementById("breaksSummaryText");
const breakTimerValue = document.getElementById("breakTimerValue");
const breakHint = document.getElementById("breakHint");
const blinkLogBody = document.getElementById("blinkLogBody");
const logCountBadge = document.getElementById("logCountBadge");

const ecoToggle = document.getElementById("ecoToggle");
const hideVideoToggle = document.getElementById("hideVideoToggle");
const hiddenPreviewOverlay = document.getElementById("hiddenPreviewOverlay");
const showVideoBtn = document.getElementById("showVideoBtn");
const idleBackoffToggle = document.getElementById("idleBackoffToggle");
const dutyCycleToggle = document.getElementById("dutyCycleToggle");
const lowBpmSlider = document.getElementById("lowBpmSlider");
const lowBpmReadout = document.getElementById("lowBpmReadout");
const legendLowBpm = document.getElementById("legendLowBpm");
const drowsySlider = document.getElementById("drowsySlider");
const drowsyReadout = document.getElementById("drowsyReadout");
const sensitivitySelect = document.getElementById("sensitivitySelect");
const popupToggle = document.getElementById("popupToggle");
const testAlertBtn = document.getElementById("testAlertBtn");
const soundToggle = document.getElementById("soundToggle");
const overlayToggle = document.getElementById("overlayToggle");
const mirrorToggle = document.getElementById("mirrorToggle");
const breakToggle = document.getElementById("breakToggle");

const alertModalBackdrop = document.getElementById("alertModalBackdrop");
const alertModalCard = document.getElementById("alertModalCard");
const alertModalIcon = document.getElementById("alertModalIcon");
const alertModalTitle = document.getElementById("alertModalTitle");
const alertModalBody = document.getElementById("alertModalBody");
const alertModalCountdown = document.getElementById("alertModalCountdown");
const alertModalCloseBtn = document.getElementById("alertModalCloseBtn");

// Runtime state
let faceLandmarker = null;
let mediaStream = null;
let rafId = null;
let bgTimerId = null;
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
  activeWindowStartMs: null,
  activeMonitoringMs: 0,
  lastActiveTickMs: null,
  cameraWarmupUntilMs: 0,
  totalBlinks: 0,
  drowsyEvents: 0,
  dryEyeAlerts: 0,
  breaksCompleted: 0,
  baselineOpenRatio: null,
  internalThreshold: SENSITIVITY_MAP.standard.defaultThreshold,
  hysteresis: 0.02,
  smoothingAlpha: 0.45,
  smoothedSignal: null,
  eyesClosed: false,
  closedFrames: 0,
  closureStartMs: null,
  lastBlinkMs: null,
  drowsyTriggeredForClosure: false,
  lastDryEyeAlertMs: null,
  calibrating: false,
  calibrationStartMs: null,
  calibrationSamples: [],
  blinkTimestamps: [],
  blinkRecords: [],
  bpmHistory: [],
  lastBpmSampleMs: 0,
  lastInferMs: 0,
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
  peakBpmText.textContent = t("peakBpm", { bpm: state.maxBpm.toFixed(1) });
  breaksSummaryText.textContent = t("breaksSummary", { count: state.breaksCompleted });
  if (!running) {
    setStatusBadge(t("statusReady"), "pill-idle");
    eyeStateText.textContent = t("waitingCamera");
    rateHealthText.textContent = t("healthyRange");
  }
  updatePowerBadge(performance.now());
  drawBpmChart();
}

function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function computeEyeOpenness(landmarks, indices, width, height) {
  const pts = indices.map((i) => ({
    x: landmarks[i].x * width,
    y: landmarks[i].y * height,
  }));
  const horiz = dist(pts[0], pts[3]);
  if (horiz <= 1e-6) return { ratio: 0, pts };
  const v1 = dist(pts[1], pts[5]);
  const v2 = dist(pts[2], pts[4]);
  return { ratio: (v1 + v2) / (2 * horiz), pts };
}

function applySensitivity() {
  const preset = SENSITIVITY_MAP[sensitivitySelect.value] || SENSITIVITY_MAP.standard;
  if (state.baselineOpenRatio !== null) {
    state.internalThreshold = Math.max(0.14, Math.min(0.28, state.baselineOpenRatio * preset.ratio));
  } else {
    state.internalThreshold = preset.defaultThreshold;
  }
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
  let base = ecoToggle.checked ? 15 : 24;
  if (document.hidden) {
    base = Math.min(base, 10);
  }
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

function cancelLoop() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  if (bgTimerId !== null) {
    clearTimeout(bgTimerId);
    bgTimerId = null;
  }
}

function scheduleNextTick() {
  if (!running || inDutySleep) return;
  if (document.hidden) {
    // Minimized / backgrounded: zero visual rendering, lightweight background timer
    const fps = getEffectiveFps(performance.now());
    const delayMs = Math.max(85, Math.round(1000 / fps));
    bgTimerId = setTimeout(() => {
      bgTimerId = null;
      processFrame(performance.now(), true);
    }, delayMs);
  } else {
    rafId = requestAnimationFrame((ts) => {
      rafId = null;
      processFrame(ts, false);
    });
  }
}

function updateVideoVisibilityUI() {
  const hideNow = running && !inDutySleep && hideVideoToggle.checked;
  videoWrapper.classList.toggle("video-hidden", hideNow);
  hiddenPreviewOverlay.classList.toggle("hidden", !hideNow);
  if (hideNow) {
    overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  }
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

let modalAutoCloseTimer = null;
let activeModalKind = null;

function playTone(type = "dry_eye") {
  if (!soundToggle.checked) return;
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === "suspended") audioCtx.resume();

    // Distinct, pleasant multi-note melodies so each eye-care reminder is unmistakable
    const sequences = {
      dry_eye: [
        { freq: 659.25, delay: 0.0, dur: 0.16, wave: "sine", vol: 0.22 },
        { freq: 880.0, delay: 0.20, dur: 0.24, wave: "sine", vol: 0.24 },
      ],
      break: [
        { freq: 523.25, delay: 0.0, dur: 0.16, wave: "sine", vol: 0.22 },
        { freq: 659.25, delay: 0.18, dur: 0.16, wave: "sine", vol: 0.22 },
        { freq: 783.99, delay: 0.36, dur: 0.30, wave: "sine", vol: 0.25 },
      ],
      break_done: [
        { freq: 783.99, delay: 0.0, dur: 0.14, wave: "sine", vol: 0.20 },
        { freq: 1046.5, delay: 0.16, dur: 0.26, wave: "sine", vol: 0.22 },
      ],
      drowsy: [
        { freq: 920.0, delay: 0.0, dur: 0.18, wave: "triangle", vol: 0.26 },
        { freq: 920.0, delay: 0.24, dur: 0.18, wave: "triangle", vol: 0.26 },
        { freq: 1046.5, delay: 0.48, dur: 0.28, wave: "triangle", vol: 0.28 },
      ],
    };

    const notes = sequences[type] || sequences.dry_eye;
    const baseTime = audioCtx.currentTime;
    for (const note of notes) {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = note.wave;
      osc.frequency.setValueAtTime(note.freq, baseTime + note.delay);
      gain.gain.setValueAtTime(0.0001, baseTime + note.delay);
      gain.gain.exponentialRampToValueAtTime(note.vol, baseTime + note.delay + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, baseTime + note.delay + note.dur);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start(baseTime + note.delay);
      osc.stop(baseTime + note.delay + note.dur + 0.03);
    }
  } catch {
    // AudioContext may be blocked until user interaction
  }
}

function requestSystemNotificationPermission() {
  if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission().catch(() => {});
  }
}

function sendSystemNotification(title, body) {
  if (!popupToggle.checked) return;
  if (isTauriDesktop) return; // Handled natively via Tauri surface_alert command
  if ("Notification" in window && Notification.permission === "granted") {
    try {
      const n = new Notification(title, {
        body,
        icon: "icons/icon-192.png",
        requireInteraction: true,
        silent: false,
      });
      n.onclick = () => {
        window.focus();
        n.close();
      };
    } catch {
      // Ignore browser notification restrictions
    }
  }
}

function closeAlertModal() {
  if (modalAutoCloseTimer !== null) {
    clearTimeout(modalAutoCloseTimer);
    modalAutoCloseTimer = null;
  }
  activeModalKind = null;
  alertModalBackdrop.classList.add("hidden");
  alertModalCountdown.classList.add("hidden");
  if (isTauriDesktop) {
    tauriCore.invoke("release_always_on_top").catch(() => {});
  }
}

function showAlertModal({ kind, title, body, countdownSec = null, autoCloseMs = 10000 }) {
  if (!popupToggle.checked) return;
  if (modalAutoCloseTimer !== null) {
    clearTimeout(modalAutoCloseTimer);
    modalAutoCloseTimer = null;
  }
  activeModalKind = kind;
  const iconMap = { dry_eye: "💧", break: "🌿", break_done: "✅", drowsy: "⚠️" };
  const clsMap = { dry_eye: "modal-dry-eye", break: "modal-break", break_done: "modal-break", drowsy: "modal-drowsy" };

  alertModalIcon.textContent = iconMap[kind] || "👁️";
  alertModalCard.className = `modal-card ${clsMap[kind] || "modal-dry-eye"}`;
  alertModalTitle.textContent = title;
  alertModalBody.textContent = body;

  if (countdownSec !== null) {
    alertModalCountdown.textContent = `${Math.ceil(countdownSec)}s`;
    alertModalCountdown.classList.remove("hidden");
  } else {
    alertModalCountdown.classList.add("hidden");
  }
  alertModalBackdrop.classList.remove("hidden");

  if (autoCloseMs > 0) {
    modalAutoCloseTimer = setTimeout(closeAlertModal, autoCloseMs);
  }
}

function triggerReminder({ kind, title, body, countdownSec = null, autoCloseMs = 10000 }) {
  playTone(kind);
  showAlertModal({ kind, title, body, countdownSec, autoCloseMs });
  if (isTauriDesktop && popupToggle.checked) {
    // Surface window always-on-top & send native OS notification even when minimized to tray
    const bringToFront = kind !== "break_done";
    tauriCore.invoke("surface_alert", { title, body, bringToFront }).catch(() => {});
  } else {
    sendSystemNotification(title, body);
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

function resetTransientDetection(nowMs, warmupMs = 1500) {
  state.smoothedSignal = null;
  state.eyesClosed = false;
  state.closedFrames = 0;
  state.closureStartMs = null;
  state.drowsyTriggeredForClosure = false;
  state.cameraWarmupUntilMs = nowMs + warmupMs;
}

function beginActiveMonitoringWindow(nowMs, warmupMs = 1500) {
  resetTransientDetection(nowMs, warmupMs);
  state.activeWindowStartMs = nowMs;
  state.lastActiveTickMs = nowMs;
  state.blinkTimestamps = [];
}

function resetSession(keepCalibration = true) {
  const now = performance.now();
  state.sessionStartMs = running ? now : null;
  state.activeWindowStartMs = running ? now : null;
  state.activeMonitoringMs = 0;
  state.lastActiveTickMs = running ? now : null;
  state.cameraWarmupUntilMs = running ? now + 1500 : 0;
  state.totalBlinks = 0;
  state.drowsyEvents = 0;
  state.dryEyeAlerts = 0;
  state.breaksCompleted = 0;
  state.smoothedSignal = null;
  state.eyesClosed = false;
  state.closedFrames = 0;
  state.closureStartMs = null;
  state.lastBlinkMs = null;
  state.drowsyTriggeredForClosure = false;
  state.lastDryEyeAlertMs = null;
  state.blinkTimestamps = [];
  state.blinkRecords = [];
  state.bpmHistory = [];
  state.lastBpmSampleMs = 0;
  state.maxBpm = 0;
  state.inBreak = false;
  state.breakEndMs = null;
  state.nextBreakMs = running ? now + 20 * 60 * 1000 : null;
  if (!keepCalibration) {
    state.calibrating = false;
    state.calibrationSamples = [];
  }

  bpmValue.textContent = "0.0";
  rateHealthText.textContent = t("healthyRange");
  totalBlinksValue.textContent = "0";
  avgBpmValue.textContent = "0.0";
  peakBpmText.textContent = t("peakBpm", { bpm: "0.0" });
  sessionTimeValue.textContent = "00:00";
  breaksSummaryText.textContent = t("breaksSummary", { count: 0 });
  breakTimerValue.textContent = "20:00";
  logCountBadge.textContent = t("eventsCount", { count: 0 });
  blinkLogBody.innerHTML = `<tr><td colspan="4" class="empty-row">${t("noBlinksYet")}</td></tr>`;
  setBanner(null, "");
  drawBpmChart();
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

  let visionModule;
  let wasmRoot = CDN_WASM_ROOT;
  let modelUrl = CDN_MODEL_URL;

  try {
    // Prefer bundled offline assets (inside Tauri Desktop App)
    visionModule = await import(LOCAL_VISION_MODULE);
    wasmRoot = LOCAL_WASM_ROOT;
    modelUrl = LOCAL_MODEL_URL;
  } catch {
    visionModule = await import(CDN_VISION_MODULE);
  }

  const { FaceLandmarker, FilesetResolver } = visionModule;
  const filesetResolver = await FilesetResolver.forVisionTasks(wasmRoot);
  faceLandmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
    baseOptions: {
      modelAssetPath: modelUrl,
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
  const sleepStart = performance.now();
  state.dutyPhaseStartMs = sleepStart;
  resetTransientDetection(sleepStart, 0);
  cancelLoop();
  releaseMediaStream();
  updateVideoVisibilityUI();
  placeholderEl.classList.remove("hidden");
  startBtnPrimary.classList.add("hidden");
  setStatusBadge(t("statusDutySleep"), "pill-eco");
  setBanner(null, "");

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
        updateVideoVisibilityUI();
        const wakeNow = performance.now();
        state.dutyPhaseStartMs = wakeNow;
        state.lastFaceMs = wakeNow;
        beginActiveMonitoringWindow(wakeNow, 2000);
        setStatusBadge(t("statusLive"), "pill-live");
        updatePowerBadge(wakeNow);
        scheduleNextTick();
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
    requestSystemNotificationPermission();
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
    beginActiveMonitoringWindow(now, 1500);
    if (state.nextBreakMs === null) state.nextBreakMs = now + 20 * 60 * 1000;

    toggleCameraBtn.textContent = t("stopCamera");
    toggleCameraBtn.className = "btn btn-danger";
    toggleCameraBtn.disabled = false;
    pauseBtn.disabled = false;
    calibrateBtn.disabled = false;
    setStatusBadge(t("statusLive"), "pill-live");
    updatePowerBadge(now);
    updateVideoVisibilityUI();

    startCalibration();
    scheduleNextTick();
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
  cancelLoop();
  if (dutySleepTimerId !== null) {
    clearTimeout(dutySleepTimerId);
    dutySleepTimerId = null;
  }
  releaseMediaStream();
  updateVideoVisibilityUI();
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

function drawBpmChart() {
  const ctx = bpmChartCtx;
  const w = bpmChartCanvas.width;
  const h = bpmChartCanvas.height;
  ctx.clearRect(0, 0, w, h);

  const padLeft = 36;
  const padRight = 12;
  const padTop = 14;
  const padBottom = 16;
  const plotW = w - padLeft - padRight;
  const plotH = h - padTop - padBottom;

  const peakData = state.bpmHistory.reduce((m, s) => Math.max(m, s.bpm), 0);
  const maxBpm = Math.max(30, Math.ceil((peakData + 5) / 5) * 5);
  const toY = (v) => {
    const norm = Math.max(0, Math.min(1, v / maxBpm));
    return padTop + plotH - norm * plotH;
  };

  // Shaded healthy blink-rate band (15-20 BPM)
  const healthyTop = toY(20);
  const healthyBot = toY(15);
  ctx.fillStyle = "rgba(52, 211, 153, 0.10)";
  ctx.fillRect(padLeft, healthyTop, plotW, Math.max(2, healthyBot - healthyTop));

  // Horizontal grid + Y-axis labels
  ctx.strokeStyle = "rgba(147, 164, 199, 0.13)";
  ctx.fillStyle = "#93a4c7";
  ctx.font = "11px -apple-system, BlinkMacSystemFont, sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.lineWidth = 1;
  const step = maxBpm <= 30 ? 10 : 15;
  for (let tick = 0; tick <= maxBpm; tick += step) {
    const y = toY(tick);
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(w - padRight, y);
    ctx.stroke();
    ctx.fillText(String(tick), padLeft - 6, y);
  }

  // Dry-eye alert threshold line
  const lowLimit = parseFloat(lowBpmSlider.value);
  const ty = toY(lowLimit);
  ctx.save();
  ctx.strokeStyle = "#fbbf24";
  ctx.setLineDash([6, 5]);
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(padLeft, ty);
  ctx.lineTo(w - padRight, ty);
  ctx.stroke();
  ctx.restore();

  if (state.bpmHistory.length < 2) return;

  const n = state.bpmHistory.length;
  const pts = state.bpmHistory.map((sample, idx) => ({
    x: padLeft + (idx / Math.max(1, n - 1)) * plotW,
    y: toY(sample.bpm),
    blink: sample.blink,
  }));

  // Gradient fill under BPM curve
  const grad = ctx.createLinearGradient(0, padTop, 0, padTop + plotH);
  grad.addColorStop(0, "rgba(52, 211, 153, 0.28)");
  grad.addColorStop(1, "rgba(52, 211, 153, 0.01)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(pts[0].x, padTop + plotH);
  pts.forEach((p) => ctx.lineTo(p.x, p.y));
  ctx.lineTo(pts[pts.length - 1].x, padTop + plotH);
  ctx.closePath();
  ctx.fill();

  // BPM trend line
  ctx.strokeStyle = "#34d399";
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  pts.forEach((p, idx) => {
    if (idx === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.stroke();
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
    <td>${t("bpmUnit", { bpm: rec.blink_rate_bpm.toFixed(1) })}</td>
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
    if (activeModalKind === "break" && !alertModalBackdrop.classList.contains("hidden")) {
      alertModalCountdown.textContent = `${Math.ceil(remSec)}s`;
    }
    if (remSec <= 0) {
      state.inBreak = false;
      state.breaksCompleted += 1;
      breaksSummaryText.textContent = t("breaksSummary", { count: state.breaksCompleted });
      state.nextBreakMs = nowMs + 20 * 60 * 1000;
      triggerReminder({
        kind: "break_done",
        title: t("popupBreakDoneTitle"),
        body: t("popupBreakDoneBody"),
        autoCloseMs: 5000,
      });
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
    triggerReminder({
      kind: "break",
      title: t("popupBreakTitle"),
      body: t("popupBreakBody"),
      countdownSec: 20,
      autoCloseMs: 0,
    });
    return t("bannerBreak", { sec: 20 });
  }
  return null;
}

function processFrame(nowMs, isBackground = false) {
  if (!running || inDutySleep) return;
  scheduleNextTick();

  if (paused || videoEl.readyState < 2) return;

  if (dutyCycleToggle.checked && state.dutyPhaseStartMs !== null && nowMs - state.dutyPhaseStartMs >= DUTY_ON_MS) {
    enterDutySleep();
    return;
  }

  const targetFps = getEffectiveFps(nowMs);
  const minIntervalMs = 1000 / targetFps;
  if (!isBackground && nowMs - state.lastInferMs < minIntervalMs) return;
  if (videoEl.currentTime === lastVideoTime) return;

  state.lastInferMs = nowMs;
  lastVideoTime = videoEl.currentTime;
  const skipVisualRender = isBackground || document.hidden || hideVideoToggle.checked;
  if (!isBackground && !document.hidden) {
    updatePowerBadge(nowMs);
  }

  const width = videoEl.videoWidth;
  const height = videoEl.videoHeight;
  if (overlayCanvas.width !== width || overlayCanvas.height !== height) {
    overlayCanvas.width = width;
    overlayCanvas.height = height;
  }

  const result = faceLandmarker.detectForVideo(videoEl, nowMs);
  let blinkThisFrame = false;
  let drowsyNow = false;
  let closureMs = 0;

  // Accumulate active monitoring time (excluding duty-cycle camera-off sleep & pause)
  if (state.activeWindowStartMs === null) state.activeWindowStartMs = nowMs;
  if (state.lastActiveTickMs !== null) {
    const dtMs = Math.max(0, Math.min(2000, nowMs - state.lastActiveTickMs));
    state.activeMonitoringMs += dtMs;
  }
  state.lastActiveTickMs = nowMs;

  const elapsedSec = Math.max(0, (nowMs - state.sessionStartMs) / 1000);
  const activeWindowSec = Math.max(0, (nowMs - state.activeWindowStartMs) / 1000);
  const activeTotalSec = Math.max(activeWindowSec, state.activeMonitoringMs / 1000);
  const inCameraWarmup = nowMs < state.cameraWarmupUntilMs;

  const bpmCutoff = nowMs - 60000;
  while (state.blinkTimestamps.length && state.blinkTimestamps[0] < bpmCutoff) {
    state.blinkTimestamps.shift();
  }
  const effWindow = Math.min(60, Math.max(activeWindowSec, 1));

  if (!result.faceLandmarks || result.faceLandmarks.length === 0) {
    overlayCtx.clearRect(0, 0, width, height);
    state.eyesClosed = false;
    state.closedFrames = 0;
    state.closureStartMs = null;
    eyeStateText.textContent = t("noFace");
  } else {
    state.lastFaceMs = nowMs;
    const lm = result.faceLandmarks[0];
    const left = computeEyeOpenness(lm, LEFT_EYE, width, height);
    const right = computeEyeOpenness(lm, RIGHT_EYE, width, height);
    const rawSignal = (left.ratio + right.ratio) / 2;

    state.smoothedSignal =
      state.smoothedSignal === null
        ? rawSignal
        : state.smoothingAlpha * rawSignal + (1 - state.smoothingAlpha) * state.smoothedSignal;

    if (state.calibrating) {
      if (rawSignal > 0.1) state.calibrationSamples.push(rawSignal);
      const calElapsed = (nowMs - state.calibrationStartMs) / 1000;
      const pct = Math.min(100, Math.round((calElapsed / 3.0) * 100));
      setBanner("info", t("bannerCalibrating", { pct }));
      if (calElapsed >= 3.0 && state.calibrationSamples.length >= 8) {
        const sorted = [...state.calibrationSamples].sort((a, b) => a - b);
        state.baselineOpenRatio = sorted[Math.floor(sorted.length * 0.75)];
        applySensitivity();
        state.calibrating = false;
        setBanner(null, "");
      }
    }

    const closeThr = state.internalThreshold;
    const openThr = state.internalThreshold + state.hysteresis;
    const drowsyLimitMs = parseFloat(drowsySlider.value) * 1000;

    if (!state.eyesClosed) {
      if (!inCameraWarmup && state.smoothedSignal < closeThr) {
        state.eyesClosed = true;
        state.closedFrames = 1;
        state.closureStartMs = nowMs;
        state.drowsyTriggeredForClosure = false;
      }
    } else if (state.smoothedSignal >= openThr) {
      const durMs = Math.max(0, nowMs - state.closureStartMs);
      const cooldownOk = state.lastBlinkMs === null || nowMs - state.lastBlinkMs >= 140;
      if (!state.calibrating && state.closedFrames >= 2 && durMs >= 50 && durMs <= 800 && cooldownOk) {
        state.totalBlinks += 1;
        state.lastBlinkMs = nowMs;
        state.blinkTimestamps.push(nowMs);
        blinkThisFrame = true;

        const rateNow = activeWindowSec < 5 ? 0 : (state.blinkTimestamps.length / effWindow) * 60;
        const rec = {
          blink_index: state.totalBlinks,
          iso_time: new Date().toISOString(),
          clock_time: new Date().toLocaleTimeString(),
          elapsed_sec: Number(elapsedSec.toFixed(2)),
          duration_ms: Number(durMs.toFixed(1)),
          blink_rate_bpm: Number(rateNow.toFixed(1)),
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
      if (!state.calibrating && !inCameraWarmup && closureMs >= drowsyLimitMs) {
        drowsyNow = true;
        if (!state.drowsyTriggeredForClosure) {
          state.drowsyTriggeredForClosure = true;
          state.drowsyEvents += 1;
          triggerReminder({
            kind: "drowsy",
            title: t("popupDrowsyTitle"),
            body: t("popupDrowsyBody", { sec: (closureMs / 1000).toFixed(1) }),
            autoCloseMs: 8000,
          });
        }
      }
    }

    if (!skipVisualRender) {
      drawEyeOverlay(left.pts, right.pts, state.eyesClosed);
    }
    if (!isBackground && !document.hidden) {
      eyeStateText.textContent = state.eyesClosed ? t("eyesClosed") : t("eyesOpen");
    }
  }

  const currentBpm = activeWindowSec < 5 ? 0 : (state.blinkTimestamps.length / effWindow) * 60;
  const avgBpm = activeTotalSec < 5 ? 0 : (state.totalBlinks / activeTotalSec) * 60;
  if (currentBpm > state.maxBpm) state.maxBpm = currentBpm;

  // Record 1 BPM trend sample per second; skip chart painting while minimized
  const sampleInterval = hideVideoToggle.checked ? 2000 : 1000;
  if (blinkThisFrame || nowMs - state.lastBpmSampleMs >= sampleInterval) {
    state.lastBpmSampleMs = nowMs;
    state.bpmHistory.push({ bpm: Number(currentBpm.toFixed(1)), blink: blinkThisFrame });
    if (state.bpmHistory.length > 120) state.bpmHistory.shift();
    if (!isBackground && !document.hidden) {
      drawBpmChart();
    }
    if (isTauriDesktop) {
      tauriCore
        .invoke("update_tray_tooltip", {
          text: t("trayTooltip", { bpm: currentBpm.toFixed(1), blinks: state.totalBlinks }),
        })
        .catch(() => {});
    }
  }

  if (!isBackground && !document.hidden) {
    totalBlinksValue.textContent = String(state.totalBlinks);
    bpmValue.textContent = currentBpm.toFixed(1);
    avgBpmValue.textContent = avgBpm.toFixed(1);
    peakBpmText.textContent = t("peakBpm", { bpm: state.maxBpm.toFixed(1) });
    sessionTimeValue.textContent = formatDuration(elapsedSec);
    breaksSummaryText.textContent = t("breaksSummary", { count: state.breaksCompleted });
  }

  const breakMsg = updateBreakTimer(nowMs);
  const lowBpmLimit = parseFloat(lowBpmSlider.value);
  // Require at least 30s of active camera monitoring in the current sampling window before alerting low BPM
  const dryEyeWarn = !state.calibrating && activeWindowSec >= 30 && currentBpm < lowBpmLimit;
  if (dryEyeWarn && (state.lastDryEyeAlertMs === null || nowMs - state.lastDryEyeAlertMs >= 45000)) {
    state.lastDryEyeAlertMs = nowMs;
    state.dryEyeAlerts += 1;
    triggerReminder({
      kind: "dry_eye",
      title: t("popupDryEyeTitle"),
      body: t("popupDryEyeBody", { bpm: currentBpm.toFixed(1) }),
      autoCloseMs: 9000,
    });
  }

  if (activeWindowSec < 5) {
    rateHealthText.textContent = t("rateWarmup");
  } else if (dryEyeWarn) {
    rateHealthText.textContent = t("rateLow");
  } else {
    rateHealthText.textContent = t("rateHealthy");
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
  const header = ["blink_index", "iso_time", "elapsed_sec", "duration_ms", "blink_rate_bpm"];
  const rows = state.blinkRecords.map((r) => header.map((k) => r[k]).join(","));
  const csv = [header.join(","), ...rows].join("\n");
  downloadFile(`blink-counter-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`, csv, "text/csv");
}

function exportJson() {
  const elapsedSec = state.sessionStartMs ? (performance.now() - state.sessionStartMs) / 1000 : 0;
  const activeSec = Math.max(0, state.activeMonitoringMs / 1000);
  const payload = {
    exported_at: new Date().toISOString(),
    language: currentLang,
    eco_mode: ecoToggle.checked,
    metrics: {
      total_blinks: state.totalBlinks,
      duration_sec: Number(elapsedSec.toFixed(2)),
      active_monitoring_sec: Number(activeSec.toFixed(2)),
      avg_bpm: activeSec >= 5 ? Number(((state.totalBlinks / activeSec) * 60).toFixed(1)) : 0,
      max_bpm: Number(state.maxBpm.toFixed(1)),
      drowsy_events: state.drowsyEvents,
      dry_eye_alerts: state.dryEyeAlerts,
      breaks_completed: state.breaksCompleted,
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
hideVideoToggle.addEventListener("change", () => updateVideoVisibilityUI());
showVideoBtn.addEventListener("click", () => {
  hideVideoToggle.checked = false;
  updateVideoVisibilityUI();
});
idleBackoffToggle.addEventListener("change", () => updatePowerBadge(performance.now()));

// Automatically stop all visual/canvas/chart rendering when minimized or backgrounded
document.addEventListener("visibilitychange", () => {
  if (!running || inDutySleep) return;
  cancelLoop();
  if (!document.hidden) {
    updatePowerBadge(performance.now());
    drawBpmChart();
  }
  scheduleNextTick();
});
dutyCycleToggle.addEventListener("change", () => {
  state.dutyPhaseStartMs = performance.now();
  updatePowerBadge(performance.now());
});
sensitivitySelect.addEventListener("change", applySensitivity);

toggleCameraBtn.addEventListener("click", () => (running ? stopCamera() : startCamera()));
startBtnPrimary.addEventListener("click", startCamera);
pauseBtn.addEventListener("click", () => {
  paused = !paused;
  const now = performance.now();
  if (paused) {
    resetTransientDetection(now, 0);
  } else {
    beginActiveMonitoringWindow(now, 1000);
  }
  pauseBtn.textContent = paused ? t("resume") : t("pause");
  setStatusBadge(paused ? t("statusPaused") : t("statusLive"), paused ? "pill-warn" : "pill-live");
});
calibrateBtn.addEventListener("click", startCalibration);
resetBtn.addEventListener("click", () => resetSession(true));
exportCsvBtn.addEventListener("click", exportCsv);
exportJsonBtn.addEventListener("click", exportJson);
takeBreakNowBtn.addEventListener("click", () => {
  requestSystemNotificationPermission();
  const now = performance.now();
  state.inBreak = true;
  state.breakEndMs = now + 20 * 1000;
  triggerReminder({
    kind: "break",
    title: t("popupBreakTitle"),
    body: t("popupBreakBody"),
    countdownSec: 20,
    autoCloseMs: 0,
  });
});

popupToggle.addEventListener("change", () => {
  if (popupToggle.checked) requestSystemNotificationPermission();
});

testAlertBtn.addEventListener("click", () => {
  requestSystemNotificationPermission();
  triggerReminder({
    kind: "dry_eye",
    title: t("popupDryEyeTitle"),
    body: t("popupDryEyeBody", { bpm: "6.0" }),
    autoCloseMs: 8000,
  });
});

alertModalCloseBtn.addEventListener("click", closeAlertModal);
alertModalBackdrop.addEventListener("click", (e) => {
  if (e.target === alertModalBackdrop) closeAlertModal();
});

lowBpmSlider.addEventListener("input", (e) => {
  lowBpmReadout.textContent = e.target.value;
  legendLowBpm.textContent = e.target.value;
  drawBpmChart();
});
drowsySlider.addEventListener("input", (e) => {
  drowsyReadout.textContent = `${parseFloat(e.target.value).toFixed(1)}s`;
});
mirrorToggle.addEventListener("change", () => {
  videoWrapper.classList.toggle("mirrored", mirrorToggle.checked);
});

// Keep 20-20-20 break countdown ticking even if camera is stopped or paused
setInterval(() => {
  if (state.inBreak && (!running || paused || inDutySleep)) {
    updateBreakTimer(performance.now());
  }
}, 500);

// Initialize UI
videoWrapper.classList.add("mirrored");
applyStaticTranslations();
drawBpmChart();

// Progressive Web App (PWA) install support & Tauri Desktop Tray / Autostart controls
const installAppBtn = document.getElementById("installAppBtn");
const minimizeTrayBtn = document.getElementById("minimizeTrayBtn");
const autostartRow = document.getElementById("autostartRow");
const autostartToggle = document.getElementById("autostartToggle");
let deferredInstallPrompt = null;

if (isTauriDesktop) {
  if (minimizeTrayBtn) {
    minimizeTrayBtn.classList.remove("hidden");
    minimizeTrayBtn.addEventListener("click", () => {
      tauriCore.invoke("minimize_to_tray").catch(() => {});
    });
  }
  if (autostartRow && autostartToggle) {
    autostartRow.classList.remove("hidden");
    tauriCore
      .invoke("get_autostart")
      .then((enabled) => {
        autostartToggle.checked = Boolean(enabled);
      })
      .catch(() => {});
    autostartToggle.addEventListener("change", () => {
      const desired = autostartToggle.checked;
      tauriCore
        .invoke("set_autostart", { enabled: desired })
        .then((actual) => {
          autostartToggle.checked = Boolean(actual);
        })
        .catch(() => {
          autostartToggle.checked = !desired;
        });
    });
  }
  if (tauriEvent) {
    tauriEvent
      .listen("tray-start-break", () => {
        takeBreakNowBtn.click();
      })
      .catch(() => {});
  }
} else if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => {});
  });
}

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  if (installAppBtn) installAppBtn.classList.remove("hidden");
});

if (installAppBtn) {
  installAppBtn.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    installAppBtn.classList.add("hidden");
  });
}

window.addEventListener("appinstalled", () => {
  deferredInstallPrompt = null;
  if (installAppBtn) installAppBtn.classList.add("hidden");
});
