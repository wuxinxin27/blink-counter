"""Power-saving & eco-mode controller: FPS throttling, idle backoff, and duty-cycle sampling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class PowerConfig:
    """Controls CPU/GPU/camera energy usage."""

    eco_mode: bool = False
    target_fps: float = 30.0
    eco_fps: float = 15.0
    idle_backoff: bool = True
    idle_after_sec: float = 5.0
    idle_fps: float = 1.5
    duty_on_sec: float = 0.0   # > 0 enables periodic camera duty-cycling
    duty_off_sec: float = 0.0  # > 0 releases camera completely between windows


@dataclass(frozen=True)
class DutyState:
    """Current phase of periodic camera duty-cycling."""

    enabled: bool
    camera_active: bool
    phase_remaining_sec: float


def parse_duty_cycle(spec: Optional[str]) -> Tuple[float, float]:
    """Parse a `ON_SEC:OFF_SEC` string (e.g. `'60:240'`) into `(on_sec, off_sec)`."""
    if not spec:
        return (0.0, 0.0)
    parts = spec.strip().split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid --duty-cycle value {spec!r}. Expected format ON_SEC:OFF_SEC (e.g. 60:240)."
        )
    on_sec = float(parts[0])
    off_sec = float(parts[1])
    if on_sec <= 0 or off_sec <= 0:
        raise ValueError("--duty-cycle ON and OFF durations must both be positive numbers.")
    return (on_sec, off_sec)


class PowerController:
    """Manages frame pacing, no-face idle backoff, and camera duty-cycle sleep."""

    def __init__(self, config: Optional[PowerConfig] = None) -> None:
        self.config = config or PowerConfig()
        self.eco_mode: bool = self.config.eco_mode
        self._last_process_ts: Optional[float] = None
        self._last_face_ts: Optional[float] = None
        self._duty_start_ts: Optional[float] = None

    def reset(self, now: Optional[float] = None) -> None:
        self._last_process_ts = None
        self._last_face_ts = now
        self._duty_start_ts = now

    def toggle_eco_mode(self) -> bool:
        """Toggle eco mode on/off dynamically at runtime."""
        self.eco_mode = not self.eco_mode
        return self.eco_mode

    def note_face_seen(self, timestamp: float, face_detected: bool) -> None:
        """Record whether a face was detected to govern idle backoff."""
        if self._last_face_ts is None:
            self._last_face_ts = timestamp
        if face_detected:
            self._last_face_ts = timestamp

    def is_idle(self, timestamp: float) -> bool:
        """Return True if no face has been detected for >= `idle_after_sec`."""
        if not self.config.idle_backoff or self._last_face_ts is None:
            return False
        return (timestamp - self._last_face_ts) >= self.config.idle_after_sec

    def effective_fps(self, timestamp: float) -> float:
        """Compute the active frame-processing rate cap in FPS."""
        base = self.config.eco_fps if self.eco_mode else self.config.target_fps
        base = max(1.0, base)
        if self.is_idle(timestamp):
            return min(base, max(0.5, self.config.idle_fps))
        return base

    def should_process(self, timestamp: float) -> bool:
        """Return True when enough time has elapsed to process the next frame."""
        interval = 1.0 / self.effective_fps(timestamp)
        if self._last_process_ts is None or (timestamp - self._last_process_ts) >= interval:
            self._last_process_ts = timestamp
            return True
        return False

    def recommended_sleep_sec(self, timestamp: float) -> float:
        """Return how long a headless loop can sleep before the next scheduled frame."""
        interval = 1.0 / self.effective_fps(timestamp)
        if self._last_process_ts is None:
            return 0.0
        remaining = interval - (timestamp - self._last_process_ts)
        return max(0.0, min(0.5, remaining))

    def duty_state(self, timestamp: float) -> DutyState:
        """Evaluate whether the physical camera should currently be open or sleeping."""
        on_s = self.config.duty_on_sec
        off_s = self.config.duty_off_sec
        if on_s <= 0.0 or off_s <= 0.0:
            return DutyState(enabled=False, camera_active=True, phase_remaining_sec=0.0)

        if self._duty_start_ts is None:
            self._duty_start_ts = timestamp

        period = on_s + off_s
        elapsed = max(0.0, timestamp - self._duty_start_ts) % period
        if elapsed < on_s:
            return DutyState(
                enabled=True,
                camera_active=True,
                phase_remaining_sec=on_s - elapsed,
            )
        return DutyState(
            enabled=True,
            camera_active=False,
            phase_remaining_sec=period - elapsed,
        )
