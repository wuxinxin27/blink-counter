"""Eye-wellness analytics: live BPM, BPM trend history, dry-eye alerts, 20-20-20 break timer, and sound alerts."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional, Sequence, Tuple

from .config import WellnessConfig

_POPUP_LOCK = threading.Lock()
_ACTIVE_POPUP_PROC: Optional[subprocess.Popen] = None


@dataclass(frozen=True)
class BreakReminderStatus:
    """State of the 20-20-20 eye-break timer."""

    enabled: bool
    in_break: bool
    seconds_until_next_break: float
    break_seconds_remaining: float
    break_started: bool
    break_completed: bool
    breaks_completed: int


@dataclass(frozen=True)
class WellnessSnapshot:
    """Per-frame eye wellness metrics."""

    elapsed_sec: float
    current_bpm: float
    avg_bpm: float
    max_bpm: float
    low_bpm_threshold: float
    dry_eye_warning: bool
    dry_eye_triggered: bool
    dry_eye_alerts: int
    break_status: BreakReminderStatus


class WellnessMonitor:
    """Tracks blink rate (BPM), trend history, dry-eye alerts, and 20-20-20 break intervals."""

    def __init__(self, config: Optional[WellnessConfig] = None) -> None:
        self.config = config or WellnessConfig()
        self.reset()

    def reset(self, start_time: Optional[float] = None) -> None:
        self._start_ts: Optional[float] = start_time
        self._blink_timestamps: Deque[float] = deque()
        self._bpm_history: Deque[Tuple[float, float]] = deque(maxlen=180)
        self._last_history_ts: Optional[float] = None
        self._total_blinks: int = 0
        self._max_bpm: float = 0.0
        self._dry_eye_alerts: int = 0
        self._last_dry_eye_alert_ts: Optional[float] = None

        self._next_break_ts: Optional[float] = (
            start_time + self.config.break_interval_sec
            if start_time is not None and self.config.enable_break_reminder
            else None
        )
        self._in_break: bool = False
        self._break_end_ts: Optional[float] = None
        self._breaks_completed: int = 0

    @property
    def bpm_history(self) -> Sequence[Tuple[float, float]]:
        """Recent `(timestamp, current_bpm)` points for plotting the blink-rate trend."""
        return self._bpm_history

    def record_blink(self, timestamp: float) -> None:
        """Record a blink timestamp for BPM calculation."""
        if self._start_ts is None:
            self._init_timers(timestamp)
        self._blink_timestamps.append(timestamp)
        self._total_blinks += 1

    def update(self, timestamp: float, *, blink_occurred: bool = False) -> WellnessSnapshot:
        """Advance wellness timers and return the latest metrics snapshot."""
        if self._start_ts is None:
            self._init_timers(timestamp)

        if blink_occurred:
            self.record_blink(timestamp)

        assert self._start_ts is not None
        elapsed = max(0.0, timestamp - self._start_ts)

        # Prune rolling BPM window
        window = max(1.0, self.config.bpm_window_sec)
        cutoff = timestamp - window
        while self._blink_timestamps and self._blink_timestamps[0] < cutoff:
            self._blink_timestamps.popleft()

        effective_window = min(window, max(elapsed, 1.0))
        if elapsed < 5.0:
            current_bpm = 0.0
        else:
            current_bpm = (len(self._blink_timestamps) / effective_window) * 60.0

        avg_bpm = (self._total_blinks / elapsed) * 60.0 if elapsed >= 5.0 else 0.0
        if current_bpm > self._max_bpm:
            self._max_bpm = current_bpm

        # Record ~1 BPM trend sample per second (or immediately on a blink)
        if (
            self._last_history_ts is None
            or blink_occurred
            or (timestamp - self._last_history_ts) >= 1.0
        ):
            self._last_history_ts = timestamp
            self._bpm_history.append((timestamp, round(current_bpm, 1)))

        # Dry-eye / low blink rate alert
        dry_eye_warning = (
            elapsed >= self.config.low_bpm_warmup_sec
            and current_bpm < self.config.low_bpm_threshold
        )
        dry_eye_triggered = False
        if dry_eye_warning:
            cooldown_ok = (
                self._last_dry_eye_alert_ts is None
                or (timestamp - self._last_dry_eye_alert_ts) >= self.config.low_bpm_alert_cooldown_sec
            )
            if cooldown_ok:
                self._last_dry_eye_alert_ts = timestamp
                self._dry_eye_alerts += 1
                dry_eye_triggered = True

        # 20-20-20 break timer
        break_status = self._update_break_timer(timestamp)

        return WellnessSnapshot(
            elapsed_sec=elapsed,
            current_bpm=round(current_bpm, 1),
            avg_bpm=round(avg_bpm, 1),
            max_bpm=round(self._max_bpm, 1),
            low_bpm_threshold=self.config.low_bpm_threshold,
            dry_eye_warning=dry_eye_warning,
            dry_eye_triggered=dry_eye_triggered,
            dry_eye_alerts=self._dry_eye_alerts,
            break_status=break_status,
        )

    def _init_timers(self, timestamp: float) -> None:
        self._start_ts = timestamp
        if self.config.enable_break_reminder and self.config.break_interval_sec > 0:
            self._next_break_ts = timestamp + self.config.break_interval_sec
        else:
            self._next_break_ts = None

    def _update_break_timer(self, timestamp: float) -> BreakReminderStatus:
        enabled = self.config.enable_break_reminder and self.config.break_interval_sec > 0
        if not enabled:
            return BreakReminderStatus(
                enabled=False,
                in_break=False,
                seconds_until_next_break=0.0,
                break_seconds_remaining=0.0,
                break_started=False,
                break_completed=False,
                breaks_completed=self._breaks_completed,
            )

        break_started = False
        break_completed = False

        if self._in_break:
            assert self._break_end_ts is not None
            remaining = self._break_end_ts - timestamp
            if remaining <= 0.0:
                self._in_break = False
                self._break_end_ts = None
                self._breaks_completed += 1
                self._next_break_ts = timestamp + self.config.break_interval_sec
                break_completed = True
                return BreakReminderStatus(
                    enabled=True,
                    in_break=False,
                    seconds_until_next_break=self.config.break_interval_sec,
                    break_seconds_remaining=0.0,
                    break_started=False,
                    break_completed=True,
                    breaks_completed=self._breaks_completed,
                )
            return BreakReminderStatus(
                enabled=True,
                in_break=True,
                seconds_until_next_break=0.0,
                break_seconds_remaining=remaining,
                break_started=False,
                break_completed=False,
                breaks_completed=self._breaks_completed,
            )

        if self._next_break_ts is None:
            self._next_break_ts = timestamp + self.config.break_interval_sec

        until_next = self._next_break_ts - timestamp
        if until_next <= 0.0:
            self._in_break = True
            self._break_end_ts = timestamp + self.config.break_duration_sec
            break_started = True
            return BreakReminderStatus(
                enabled=True,
                in_break=True,
                seconds_until_next_break=0.0,
                break_seconds_remaining=self.config.break_duration_sec,
                break_started=True,
                break_completed=False,
                breaks_completed=self._breaks_completed,
            )

        return BreakReminderStatus(
            enabled=True,
            in_break=False,
            seconds_until_next_break=until_next,
            break_seconds_remaining=0.0,
            break_started=break_started,
            break_completed=break_completed,
            breaks_completed=self._breaks_completed,
        )


def _escape_applescript(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def play_alert_sound(kind: str = "dry_eye") -> None:
    """Play a distinct, non-blocking cross-platform alert melody on macOS, Windows, or Linux.

    Supported kinds: ``"dry_eye"``, ``"break"``, ``"break_done"``, ``"drowsy"``, ``"gentle"``.
    """

    def _play() -> None:
        try:
            if sys.platform == "darwin":
                afplay = shutil.which("afplay")
                if afplay:
                    sound_map = {
                        "dry_eye": [
                            ("/System/Library/Sounds/Glass.aiff", 0.18),
                            ("/System/Library/Sounds/Glass.aiff", 0.0),
                        ],
                        "break": [
                            ("/System/Library/Sounds/Hero.aiff", 0.0),
                        ],
                        "break_done": [
                            ("/System/Library/Sounds/Pop.aiff", 0.0),
                        ],
                        "drowsy": [
                            ("/System/Library/Sounds/Ping.aiff", 0.22),
                            ("/System/Library/Sounds/Ping.aiff", 0.22),
                            ("/System/Library/Sounds/Ping.aiff", 0.0),
                        ],
                    }
                    seq = sound_map.get(kind, [("/System/Library/Sounds/Glass.aiff", 0.0)])
                    for sound_file, pause_after in seq:
                        subprocess.run(
                            [afplay, sound_file],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False,
                        )
                        if pause_after > 0:
                            time.sleep(pause_after)
                    return
            elif sys.platform == "win32":
                import winsound  # type: ignore[import-not-found]

                melodies = {
                    "dry_eye": [(659, 140), (880, 180)],
                    "break": [(523, 140), (659, 140), (784, 220)],
                    "break_done": [(784, 120), (1046, 180)],
                    "drowsy": [(1046, 200), (1046, 200), (1046, 240)],
                }
                for freq, dur in melodies.get(kind, [(784, 160)]):
                    winsound.Beep(freq, dur)
                    time.sleep(0.06)
                return
            else:
                paplay = shutil.which("paplay")
                if paplay:
                    sound = (
                        "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"
                        if kind == "drowsy"
                        else "/usr/share/sounds/freedesktop/stereo/complete.oga"
                    )
                    subprocess.Popen(
                        [paplay, sound],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return
            sys.stdout.write("\a")
            sys.stdout.flush()
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()


def show_desktop_popup(
    title: str,
    message: str,
    *,
    kind: str = "dry_eye",
    timeout_sec: int = 8,
) -> None:
    """Display a non-blocking, auto-dismissing OS pop-up & notification across macOS, Windows, Linux."""

    def _dispatch() -> None:
        global _ACTIVE_POPUP_PROC
        try:
            if sys.platform == "darwin":
                osascript = shutil.which("osascript")
                if not osascript:
                    return
                safe_title = _escape_applescript(title)
                safe_msg = _escape_applescript(message)
                # 1. Native Notification Center banner (persists in notification history)
                subprocess.Popen(
                    [
                        osascript,
                        "-e",
                        f'display notification "{safe_msg}" with title "{safe_title}"',
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # 2. Prominent always-on-top native macOS dialog that auto-closes after timeout_sec
                alert_style = "critical" if kind == "drowsy" else "informational"
                script = (
                    f'display alert "{safe_title}" message "{safe_msg}" '
                    f'as {alert_style} giving up after {max(3, int(timeout_sec))}'
                )
                with _POPUP_LOCK:
                    if _ACTIVE_POPUP_PROC is not None and _ACTIVE_POPUP_PROC.poll() is None:
                        _ACTIVE_POPUP_PROC.terminate()
                    _ACTIVE_POPUP_PROC = subprocess.Popen(
                        [osascript, "-e", script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                return

            if sys.platform == "win32":
                # Use PowerShell WScript.Shell Popup (supports auto-dismiss timeout + topmost flag 4096)
                ps = shutil.which("powershell") or shutil.which("pwsh")
                if ps:
                    safe_title = title.replace("'", "''")
                    safe_msg = message.replace("'", "''")
                    icon_flag = 48 if kind == "drowsy" else 64
                    ps_cmd = (
                        "$ws = New-Object -ComObject WScript.Shell; "
                        f"$ws.Popup('{safe_msg}', {max(3, int(timeout_sec))}, '{safe_title}', {icon_flag + 4096}) | Out-Null"
                    )
                    with _POPUP_LOCK:
                        if _ACTIVE_POPUP_PROC is not None and _ACTIVE_POPUP_PROC.poll() is None:
                            _ACTIVE_POPUP_PROC.terminate()
                        _ACTIVE_POPUP_PROC = subprocess.Popen(
                            [ps, "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    return
                import ctypes

                flags = 0x00001000 | (0x30 if kind == "drowsy" else 0x40)
                ctypes.windll.user32.MessageBoxW(0, message, title, flags)  # type: ignore[attr-defined]
                return

            # Linux: desktop notification + optional zenity popup dialog
            notify_send = shutil.which("notify-send")
            if notify_send:
                urgency = "critical" if kind == "drowsy" else "normal"
                subprocess.Popen(
                    [notify_send, "-u", urgency, "-t", str(max(3, int(timeout_sec)) * 1000), title, message],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            zenity = shutil.which("zenity")
            if zenity:
                flag = "--warning" if kind == "drowsy" else "--info"
                with _POPUP_LOCK:
                    if _ACTIVE_POPUP_PROC is not None and _ACTIVE_POPUP_PROC.poll() is None:
                        _ACTIVE_POPUP_PROC.terminate()
                    _ACTIVE_POPUP_PROC = subprocess.Popen(
                        [
                            zenity,
                            flag,
                            "--title",
                            title,
                            "--text",
                            message,
                            "--timeout",
                            str(max(3, int(timeout_sec))),
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
        except Exception:
            pass

    threading.Thread(target=_dispatch, daemon=True).start()
