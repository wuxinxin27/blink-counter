"""Internationalization (i18n) support for English, Simplified Chinese, Japanese, and Spanish."""

from __future__ import annotations

import locale
import os
from typing import Dict, List, Tuple

SUPPORTED_LANGUAGES: Tuple[str, ...] = ("en", "zh", "ja", "es")

LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English",
    "zh": "简体中文",
    "ja": "日本語",
    "es": "Español",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "window_title": "Blink Counter - Eye Wellness Tracker",
        "blinks": "BLINKS",
        "rate_bpm": "RATE (BPM)",
        "ear_thr": "EAR (THR {thr:.2f})",
        "no_face": "NO FACE",
        "session": "SESSION",
        "next_break": "NEXT BREAK",
        "break_short": "BREAK {sec}s",
        "muted": "MUTED",
        "sound_on": "SOUND ON",
        "paused": "PAUSED",
        "eco_badge": "ECO {fps:.0f}FPS",
        "idle_badge": "IDLE {fps:.1f}FPS",
        "calibrating_banner": "Calibrating open-eye baseline... look naturally at the screen ({pct}%)",
        "drowsy_banner": "DROWSINESS ALERT! Eyes closed for {sec:.1f}s",
        "break_banner": "20-20-20 EYE BREAK: Look 20 ft (6 m) away for {sec}s",
        "dry_eye_banner": "LOW BLINK RATE ({bpm:.1f} BPM) - Remember to blink to prevent dry eyes!",
        "ear_waveform": "EAR Waveform",
        "hotkeys": "[Q] Quit [R] Reset [C] Cal [P] Pause [E] Eco [L] Lang [M] Mute [G] Graph [S] Save",
        "started_msg": "[blink-counter] Started ({backend}, lang={lang}, mode={mode}). {hint}",
        "hint_headless": "Headless mode - press Ctrl+C to stop.",
        "hint_window": "Press Q or ESC in the window to quit.",
        "status_ok": "OK",
        "status_drowsy": "DROWSY!",
        "status_low_bpm": "LOW BPM",
        "status_idle": "IDLE",
        "status_sleep": "CAMERA SLEEP ({sec}s)",
        "terminal_line": "Blinks: {blinks:4d} | BPM: {bpm:5.1f} | EAR: {ear:.3f} (thr {thr:.2f}) | PERCLOS: {perclos:4.1f}% | FPS: {fps:4.1f} | {status}",
        "duty_sleep_msg": "[blink-counter] Duty-cycle sleep: camera released for {sec}s to save power...",
        "duty_wake_msg": "[blink-counter] Duty-cycle wake: resuming camera monitoring for {sec}s...",
        "snapshot_saved": "[blink-counter] Snapshot saved -> {csv} & {json}",
        "session_complete": "[blink-counter] Session complete - Total blinks: {blinks}, Avg BPM: {bpm:.1f}, Duration: {dur:.1f}s",
        "logs_saved": "[blink-counter] Logs saved:\n  CSV : {csv}\n  JSON: {json}",
        "web_running": "[blink-counter] Browser Web App running at {url}",
        "web_privacy": "[blink-counter] All webcam processing runs 100% locally in your browser. Press Ctrl+C to stop.",
        "web_stopped": "[blink-counter] Web server stopped.",
        "mode_eco": "eco",
        "mode_standard": "standard",
    },
    "zh": {
        "window_title": "眨眼计数器 - 护眼健康助手",
        "blinks": "眨眼次数",
        "rate_bpm": "眨眼频率(次/分)",
        "ear_thr": "眼部纵横比(阈值 {thr:.2f})",
        "no_face": "未检测到人脸",
        "session": "本次时长",
        "next_break": "下次休息",
        "break_short": "休息 {sec}秒",
        "muted": "已静音",
        "sound_on": "声音开",
        "paused": "已暂停",
        "eco_badge": "省电 {fps:.0f}FPS",
        "idle_badge": "待机 {fps:.1f}FPS",
        "calibrating_banner": "正在校准睁眼基准值…请自然注视屏幕 ({pct}%)",
        "drowsy_banner": "疲劳预警！闭眼已持续 {sec:.1f} 秒",
        "break_banner": "20-20-20 护眼休息：请远眺 6 米外景物 {sec} 秒",
        "dry_eye_banner": "眨眼频率偏低 ({bpm:.1f} 次/分) - 请多眨眼，预防眼干疲劳！",
        "ear_waveform": "EAR 实时波形",
        "hotkeys": "[Q]退出 [R]重置 [C]校准 [P]暂停 [E]省电 [L]语言 [M]静音 [G]波形 [S]保存",
        "started_msg": "[blink-counter] 已启动（引擎={backend}，语言={lang}，模式={mode}）。{hint}",
        "hint_headless": "无界面模式 - 按 Ctrl+C 停止。",
        "hint_window": "在窗口按 Q 或 ESC 退出。",
        "status_ok": "正常",
        "status_drowsy": "疲劳预警!",
        "status_low_bpm": "眨眼偏少",
        "status_idle": "待机降频",
        "status_sleep": "摄像头休眠 ({sec}秒)",
        "terminal_line": "眨眼: {blinks:4d} | 频率: {bpm:5.1f}/分 | EAR: {ear:.3f} (阈值 {thr:.2f}) | PERCLOS: {perclos:4.1f}% | FPS: {fps:4.1f} | {status}",
        "duty_sleep_msg": "[blink-counter] 省电采样休眠：已释放摄像头 {sec} 秒以降低功耗…",
        "duty_wake_msg": "[blink-counter] 省电采样唤醒：恢复摄像头监测 {sec} 秒…",
        "snapshot_saved": "[blink-counter] 快照已保存 -> {csv} & {json}",
        "session_complete": "[blink-counter] 本次监测结束 - 总眨眼: {blinks} 次，平均频率: {bpm:.1f} 次/分，时长: {dur:.1f} 秒",
        "logs_saved": "[blink-counter] 日志已保存：\n  CSV : {csv}\n  JSON: {json}",
        "web_running": "[blink-counter] 浏览器网页版已启动：{url}",
        "web_privacy": "[blink-counter] 所有视频均在本地浏览器内处理，不会上传。按 Ctrl+C 停止。",
        "web_stopped": "[blink-counter] 网页服务已停止。",
        "mode_eco": "省电模式",
        "mode_standard": "标准模式",
    },
    "ja": {
        "window_title": "まばたきカウンター - 目の健康トラッカー",
        "blinks": "まばたき数",
        "rate_bpm": "回数/分 (BPM)",
        "ear_thr": "EAR (閾値 {thr:.2f})",
        "no_face": "顔未検出",
        "session": "経過時間",
        "next_break": "次の休憩",
        "break_short": "休憩 {sec}秒",
        "muted": "消音",
        "sound_on": "音声オン",
        "paused": "一時停止",
        "eco_badge": "省電力 {fps:.0f}FPS",
        "idle_badge": "待機 {fps:.1f}FPS",
        "calibrating_banner": "基準値を自動校正中…画面を自然に見てください ({pct}%)",
        "drowsy_banner": "眠気警告！{sec:.1f} 秒間目が閉じています",
        "break_banner": "20-20-20 休憩：6m先を {sec} 秒間眺めてください",
        "dry_eye_banner": "まばたき減少 ({bpm:.1f} 回/分) - ドライアイ予防のため意識してまばたきを！",
        "ear_waveform": "EAR 波形",
        "hotkeys": "[Q]終了 [R]リセット [C]校正 [P]一時停止 [E]省電力 [L]言語 [M]消音 [G]波形 [S]保存",
        "started_msg": "[blink-counter] 開始しました (エンジン={backend}, 言語={lang}, モード={mode})。{hint}",
        "hint_headless": "ヘッドレスモード - Ctrl+C で終了します。",
        "hint_window": "ウィンドウで Q または ESC を押すと終了します。",
        "status_ok": "正常",
        "status_drowsy": "眠気警告!",
        "status_low_bpm": "まばたき少",
        "status_idle": "待機省電力",
        "status_sleep": "カメラスリープ ({sec}秒)",
        "terminal_line": "回数: {blinks:4d} | BPM: {bpm:5.1f} | EAR: {ear:.3f} (閾値 {thr:.2f}) | PERCLOS: {perclos:4.1f}% | FPS: {fps:4.1f} | {status}",
        "duty_sleep_msg": "[blink-counter] 省電力スリープ：カメラを {sec} 秒間解放します…",
        "duty_wake_msg": "[blink-counter] 省電力復帰：{sec} 秒間の計測を再開します…",
        "snapshot_saved": "[blink-counter] スナップショット保存 -> {csv} & {json}",
        "session_complete": "[blink-counter] セッション終了 - 合計: {blinks} 回, 平均: {bpm:.1f} BPM, 時間: {dur:.1f} 秒",
        "logs_saved": "[blink-counter] ログ保存先:\n  CSV : {csv}\n  JSON: {json}",
        "web_running": "[blink-counter] Webアプリ起動中: {url}",
        "web_privacy": "[blink-counter] カメラ映像はブラウザ内のみでローカル処理されます。Ctrl+Cで停止。",
        "web_stopped": "[blink-counter] Webサーバーを停止しました。",
        "mode_eco": "省電力",
        "mode_standard": "標準",
    },
    "es": {
        "window_title": "Contador de Parpadeos - Salud Visual",
        "blinks": "PARPADEOS",
        "rate_bpm": "RITMO (PPM)",
        "ear_thr": "EAR (UMB {thr:.2f})",
        "no_face": "SIN ROSTRO",
        "session": "SESIÓN",
        "next_break": "PRÓX. PAUSA",
        "break_short": "PAUSA {sec}s",
        "muted": "SILENCIO",
        "sound_on": "SONIDO ON",
        "paused": "PAUSADO",
        "eco_badge": "ECO {fps:.0f}FPS",
        "idle_badge": "INACTIVO {fps:.1f}FPS",
        "calibrating_banner": "Calibrando ojos abiertos... mire la pantalla naturalmente ({pct}%)",
        "drowsy_banner": "¡ALERTA DE SOMNOLENCIA! Ojos cerrados por {sec:.1f}s",
        "break_banner": "PAUSA 20-20-20: Mire a 6 metros de distancia por {sec}s",
        "dry_eye_banner": "PARPADEO BAJO ({bpm:.1f} PPM) - ¡Recuerde parpadear para evitar ojos secos!",
        "ear_waveform": "Onda EAR",
        "hotkeys": "[Q]Salir [R]Reiniciar [C]Cal [P]Pausa [E]Eco [L]Idioma [M]Silencio [G]Gráfica [S]Guardar",
        "started_msg": "[blink-counter] Iniciado (motor={backend}, idioma={lang}, modo={mode}). {hint}",
        "hint_headless": "Modo sin ventana - presione Ctrl+C para detener.",
        "hint_window": "Presione Q o ESC en la ventana para salir.",
        "status_ok": "OK",
        "status_drowsy": "¡SOMNOLENCIA!",
        "status_low_bpm": "RITMO BAJO",
        "status_idle": "INACTIVO",
        "status_sleep": "CÁMARA EN REPOSO ({sec}s)",
        "terminal_line": "Parpadeos: {blinks:4d} | PPM: {bpm:5.1f} | EAR: {ear:.3f} (umb {thr:.2f}) | PERCLOS: {perclos:4.1f}% | FPS: {fps:4.1f} | {status}",
        "duty_sleep_msg": "[blink-counter] Modo ahorro: cámara liberada por {sec}s...",
        "duty_wake_msg": "[blink-counter] Reanudando monitoreo por {sec}s...",
        "snapshot_saved": "[blink-counter] Instantánea guardada -> {csv} & {json}",
        "session_complete": "[blink-counter] Sesión terminada - Total: {blinks}, Promedio: {bpm:.1f} PPM, Duración: {dur:.1f}s",
        "logs_saved": "[blink-counter] Registros guardados:\n  CSV : {csv}\n  JSON: {json}",
        "web_running": "[blink-counter] Aplicación Web ejecutándose en {url}",
        "web_privacy": "[blink-counter] Todo el video se procesa 100% localmente en su navegador. Ctrl+C para salir.",
        "web_stopped": "[blink-counter] Servidor web detenido.",
        "mode_eco": "eco",
        "mode_standard": "estándar",
    },
}


def detect_system_language() -> str:
    """Detect the preferred supported language from the host OS locale."""
    candidates: List[str] = []
    for env_key in ("BLINK_COUNTER_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(env_key)
        if val:
            candidates.append(val)
    try:
        loc, _ = locale.getdefaultlocale()  # type: ignore[attr-defined]
        if loc:
            candidates.append(loc)
    except Exception:
        pass

    for raw in candidates:
        lower = raw.lower()
        for code in SUPPORTED_LANGUAGES:
            if lower.startswith(code):
                return code
    return "en"


def normalize_language(lang: str) -> str:
    """Resolve `'auto'` or any locale prefix into a supported language code."""
    raw = (lang or "auto").strip().lower()
    if raw == "auto":
        return detect_system_language()
    for code in SUPPORTED_LANGUAGES:
        if raw == code or raw.startswith(f"{code}_") or raw.startswith(f"{code}-"):
            return code
    raise ValueError(
        f"Unsupported language {lang!r}. Choose from: auto, {', '.join(SUPPORTED_LANGUAGES)}."
    )


class Translator:
    """Simple stateful translator with live language cycling."""

    def __init__(self, lang: str = "auto") -> None:
        self._lang = normalize_language(lang)

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def language_name(self) -> str:
        return LANGUAGE_NAMES[self._lang]

    def set_language(self, lang: str) -> str:
        self._lang = normalize_language(lang)
        return self._lang

    def cycle_language(self) -> str:
        """Advance to the next supported language (useful for HUD hotkey `L`)."""
        idx = SUPPORTED_LANGUAGES.index(self._lang)
        self._lang = SUPPORTED_LANGUAGES[(idx + 1) % len(SUPPORTED_LANGUAGES)]
        return self._lang

    def t(self, key: str, **kwargs: object) -> str:
        """Translate `key` in the current language, falling back to English."""
        table = TRANSLATIONS.get(self._lang, TRANSLATIONS["en"])
        template = table.get(key, TRANSLATIONS["en"].get(key, key))
        return template.format(**kwargs) if kwargs else template
