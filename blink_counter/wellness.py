"""Eye-wellness analytics: live BPM, dry-eye alerts, 20-20-20 break timer, and sound alerts."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from .config import WellnessConfig


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
    dry_eye_warning: bool
    dry_eye_triggered: bool
    dry_eye_alerts: int
    break_status: BreakReminderStatus


class WellnessMonitor:
    """Tracks blink rate (BPM), dry-eye alerts, and 20-20-20 break intervals."""

    def __init__(self, config: Optional[WellnessConfig] = None) -> None:
        self.config = config or WellnessConfig()
        self.reset()

    def reset(self, start_time: Optional[float] = None) -> None:
        self._start_ts: Optional[float] = start_time
        self._blink_timestamps: Deque[float] = deque()
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

        # Scale BPM proportionally during the initial window so early readings are sensible
        effective_window = min(window, max(elapsed, 1.0))
        if elapsed < 5.0:
            current_bpm = 0.0
        else:
            current_bpm = (len(self._blink_timestamps) / effective_window) * 60.0

        avg_bpm = (self._total_blinks / elapsed) * 60.0 if elapsed >= 5.0 else 0.0
        if current_bpm > self._max_bpm:
            self._max_bpm = current_bpm

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


def play_alert_sound(kind: str = "gentle") -> None:
    """Play a non-blocking cross-platform alert tone on macOS, Windows, or Linux."""

    def _play() -> None:
        try:
            if sys.platform == "darwin":
                sound_file = (
                    "/System/Library/Sounds/Ping.aiff"
                    if kind == "drowsy"
                    else "/System/Library/Sounds/Glass.aiff"
                )
                afplay = shutil.which("afplay")
                if afplay:
                    subprocess.Popen(
                        [afplay, sound_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return
            elif sys.platform == "win32":
                import winsound  # type: ignore[import-not-found]

                freq = 1046 if kind == "drowsy" else 784
                dur = 260 if kind == "drowsy" else 140
                winsound.Beep(freq, dur)
                return
            else:
                paplay = shutil.which("paplay")
                if paplay:
                    sound = "/usr/share/sounds/freedesktop/stereo/complete.oga"
                    subprocess.Popen(
                        [paplay, sound],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return
            # Universal fallback: terminal bell
            sys.stdout.write("\a")
            sys.stdout.flush()
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()
