"""Core Eye Aspect Ratio (EAR) calculation and blink / drowsiness state machine.

This module uses only the Python standard library so it can run and be tested
identically on macOS, Linux, and Windows without camera or vision dependencies.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional, Sequence, Tuple

from .config import DetectorConfig

Point2D = Tuple[float, float]

# Canonical 6-point eye landmark indices for MediaPipe 468/478-point Face Mesh:
# [p1 (corner), p2 (upper-1), p3 (upper-2), p4 (corner), p5 (lower-2), p6 (lower-1)]
LEFT_EYE_INDICES: Tuple[int, int, int, int, int, int] = (33, 160, 158, 133, 153, 144)
RIGHT_EYE_INDICES: Tuple[int, int, int, int, int, int] = (362, 385, 387, 263, 373, 380)


def _dist(a: Point2D, b: Point2D) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def compute_ear(eye_points: Sequence[Point2D]) -> float:
    """Compute the Eye Aspect Ratio (EAR) from 6 ordered 2D eye landmarks.

    Formula (Soukupova & Cech, 2016):
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)

    Returns 0.0 if the horizontal eye distance is degenerate.
    """
    if len(eye_points) != 6:
        raise ValueError(f"Expected 6 eye landmarks, got {len(eye_points)}")

    p1, p2, p3, p4, p5, p6 = eye_points
    horizontal = _dist(p1, p4)
    if horizontal <= 1e-6:
        return 0.0
    vertical_1 = _dist(p2, p6)
    vertical_2 = _dist(p3, p5)
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


@dataclass(frozen=True)
class BlinkEvent:
    """Record of a single detected blink."""

    index: int
    timestamp: float
    duration_ms: float
    min_ear: float
    left_ear: float
    right_ear: float


@dataclass(frozen=True)
class CalibrationState:
    """Status of automatic open-eye EAR threshold calibration."""

    active: bool
    progress: float  # 0.0 .. 1.0
    baseline_ear: Optional[float]
    threshold: float


@dataclass(frozen=True)
class FrameAnalysis:
    """Per-frame output produced by :class:`BlinkDetector`."""

    timestamp: float
    face_detected: bool
    left_ear: float
    right_ear: float
    raw_ear: float
    smoothed_ear: float
    threshold: float
    eyes_closed: bool
    blink_detected: bool
    blink_event: Optional[BlinkEvent]
    total_blinks: int
    is_drowsy: bool
    drowsy_triggered: bool
    closure_duration_ms: float
    perclos: float  # Percentage (0..100) of time eyes were closed in rolling window
    calibration: CalibrationState


class BlinkDetector:
    """Stateful EAR-based blink detector with auto-calibration and drowsiness tracking."""

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        self.config = config or DetectorConfig()
        self.reset(recalibrate=self.config.auto_calibrate)

    def reset(self, *, recalibrate: Optional[bool] = None) -> None:
        """Reset all counters, filters, and calibration state."""
        self.total_blinks: int = 0
        self.drowsy_events: int = 0
        self._smoothed_ear: Optional[float] = None
        self._threshold: float = self.config.ear_threshold
        self._baseline_ear: Optional[float] = None

        self._eyes_closed: bool = False
        self._closed_frame_count: int = 0
        self._closure_start_ts: Optional[float] = None
        self._closure_min_ear: float = 1.0
        self._last_blink_ts: Optional[float] = None
        self._drowsy_active_for_closure: bool = False
        self._warmup_until_ts: Optional[float] = None

        # Calibration tracking
        do_cal = self.config.auto_calibrate if recalibrate is None else recalibrate
        self._calibrating: bool = do_cal
        self._cal_start_ts: Optional[float] = None
        self._cal_samples: list[float] = []

        # Rolling window for PERCLOS: deque of (timestamp, dt_sec, is_closed)
        self._last_ts: Optional[float] = None
        self._perclos_samples: Deque[Tuple[float, float, bool]] = deque()
        self._ear_history: Deque[Tuple[float, float]] = deque(maxlen=180)

    def start_calibration(self) -> None:
        """Trigger a fresh open-eye baseline calibration without clearing total blinks."""
        self._calibrating = True
        self._cal_start_ts = None
        self._cal_samples = []

    def reset_transient_state(self, timestamp: Optional[float] = None, *, warmup_sec: float = 1.5) -> None:
        """Clear transient eye-closure/smoothing state on resume or duty-cycle wake.

        Prevents stale closure timestamps from triggering false drowsiness alerts
        after camera sleep or pause, without clearing total blinks or calibration.
        """
        self._smoothed_ear = None
        self._eyes_closed = False
        self._closed_frame_count = 0
        self._closure_start_ts = None
        self._closure_min_ear = 1.0
        self._drowsy_active_for_closure = False
        self._last_ts = timestamp
        self._warmup_until_ts: Optional[float] = (
            timestamp + max(0.0, warmup_sec) if timestamp is not None else None
        )

    @property
    def threshold(self) -> float:
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        self._threshold = max(0.05, min(0.5, float(value)))
        self._calibrating = False

    @property
    def ear_history(self) -> Sequence[Tuple[float, float]]:
        return self._ear_history

    def update_from_landmarks(
        self,
        left_eye: Sequence[Point2D],
        right_eye: Sequence[Point2D],
        timestamp: float,
    ) -> FrameAnalysis:
        """Compute EAR from left/right 6-point eye landmarks and update state."""
        left_ear = compute_ear(left_eye)
        right_ear = compute_ear(right_eye)
        return self.update_ear(left_ear=left_ear, right_ear=right_ear, timestamp=timestamp)

    def update_no_face(self, timestamp: float) -> FrameAnalysis:
        """Handle a frame where no face was detected."""
        self._eyes_closed = False
        self._closed_frame_count = 0
        self._closure_start_ts = None
        self._drowsy_active_for_closure = False
        self._last_ts = timestamp
        perclos = self._compute_perclos(timestamp, 0.0, False)
        return FrameAnalysis(
            timestamp=timestamp,
            face_detected=False,
            left_ear=0.0,
            right_ear=0.0,
            raw_ear=0.0,
            smoothed_ear=self._smoothed_ear or 0.0,
            threshold=self._threshold,
            eyes_closed=False,
            blink_detected=False,
            blink_event=None,
            total_blinks=self.total_blinks,
            is_drowsy=False,
            drowsy_triggered=False,
            closure_duration_ms=0.0,
            perclos=perclos,
            calibration=self._calibration_state(timestamp),
        )

    def update_ear(
        self,
        left_ear: float,
        right_ear: float,
        timestamp: float,
    ) -> FrameAnalysis:
        """Update blink detector with left and right EAR values for the current frame."""
        raw_ear = (left_ear + right_ear) / 2.0

        # Exponential moving average smoothing
        alpha = self.config.smoothing_alpha
        if self._smoothed_ear is None:
            smoothed = raw_ear
        else:
            smoothed = alpha * raw_ear + (1.0 - alpha) * self._smoothed_ear
        self._smoothed_ear = smoothed
        self._ear_history.append((timestamp, smoothed))

        # Auto-calibration phase: collect upper-percentile open-eye EAR samples
        if self._calibrating:
            if self._cal_start_ts is None:
                self._cal_start_ts = timestamp
            if raw_ear > 0.10:
                self._cal_samples.append(raw_ear)
            elapsed_cal = timestamp - self._cal_start_ts
            if elapsed_cal >= self.config.calibration_duration_sec and len(self._cal_samples) >= 5:
                sorted_samples = sorted(self._cal_samples)
                # Use 75th percentile so occasional blinks during calibration don't skew baseline
                idx = min(len(sorted_samples) - 1, int(len(sorted_samples) * 0.75))
                baseline = sorted_samples[idx]
                self._baseline_ear = baseline
                adaptive = baseline * self.config.calibration_ratio
                self._threshold = max(
                    self.config.min_auto_threshold,
                    min(self.config.max_auto_threshold, adaptive),
                )
                self._calibrating = False

        dt = 0.0 if self._last_ts is None else max(0.0, min(1.0, timestamp - self._last_ts))
        self._last_ts = timestamp

        close_thresh = self._threshold
        open_thresh = self._threshold + self.config.hysteresis

        blink_event: Optional[BlinkEvent] = None
        drowsy_triggered = False
        closure_duration_ms = 0.0

        in_warmup = self._warmup_until_ts is not None and timestamp < self._warmup_until_ts
        if not self._eyes_closed:
            if not in_warmup and smoothed < close_thresh:
                self._eyes_closed = True
                self._closed_frame_count = 1
                self._closure_start_ts = timestamp
                self._closure_min_ear = smoothed
                self._drowsy_active_for_closure = False
        else:
            self._closure_min_ear = min(self._closure_min_ear, smoothed)
            if smoothed >= open_thresh:
                # Eyes reopened -> evaluate whether this closure was a valid blink
                start_ts = self._closure_start_ts if self._closure_start_ts is not None else timestamp
                duration_ms = max(0.0, (timestamp - start_ts) * 1000.0)
                cooldown_ok = (
                    self._last_blink_ts is None
                    or (timestamp - self._last_blink_ts) * 1000.0 >= self.config.cooldown_ms
                )
                if (
                    not self._calibrating
                    and self._closed_frame_count >= self.config.min_consec_frames
                    and self.config.min_blink_ms <= duration_ms <= self.config.max_blink_ms
                    and cooldown_ok
                ):
                    self.total_blinks += 1
                    self._last_blink_ts = timestamp
                    blink_event = BlinkEvent(
                        index=self.total_blinks,
                        timestamp=timestamp,
                        duration_ms=round(duration_ms, 1),
                        min_ear=round(self._closure_min_ear, 4),
                        left_ear=round(left_ear, 4),
                        right_ear=round(right_ear, 4),
                    )
                self._eyes_closed = False
                self._closed_frame_count = 0
                self._closure_start_ts = None
                self._drowsy_active_for_closure = False
            else:
                self._closed_frame_count += 1
                start_ts = self._closure_start_ts if self._closure_start_ts is not None else timestamp
                closure_duration_ms = max(0.0, (timestamp - start_ts) * 1000.0)
                if (
                    not self._calibrating
                    and closure_duration_ms >= self.config.drowsy_duration_ms
                    and not self._drowsy_active_for_closure
                ):
                    self._drowsy_active_for_closure = True
                    self.drowsy_events += 1
                    drowsy_triggered = True

        perclos = self._compute_perclos(timestamp, dt, self._eyes_closed)
        is_drowsy = self._eyes_closed and closure_duration_ms >= self.config.drowsy_duration_ms

        return FrameAnalysis(
            timestamp=timestamp,
            face_detected=True,
            left_ear=left_ear,
            right_ear=right_ear,
            raw_ear=raw_ear,
            smoothed_ear=smoothed,
            threshold=self._threshold,
            eyes_closed=self._eyes_closed,
            blink_detected=blink_event is not None,
            blink_event=blink_event,
            total_blinks=self.total_blinks,
            is_drowsy=is_drowsy,
            drowsy_triggered=drowsy_triggered,
            closure_duration_ms=closure_duration_ms,
            perclos=perclos,
            calibration=self._calibration_state(timestamp),
        )

    def _calibration_state(self, timestamp: float) -> CalibrationState:
        if not self._calibrating:
            return CalibrationState(
                active=False,
                progress=1.0,
                baseline_ear=self._baseline_ear,
                threshold=self._threshold,
            )
        if self._cal_start_ts is None or self.config.calibration_duration_sec <= 0:
            progress = 0.0
        else:
            progress = min(1.0, max(0.0, (timestamp - self._cal_start_ts) / self.config.calibration_duration_sec))
        return CalibrationState(
            active=True,
            progress=progress,
            baseline_ear=self._baseline_ear,
            threshold=self._threshold,
        )

    def _compute_perclos(self, timestamp: float, dt: float, closed: bool) -> float:
        if dt > 0.0:
            self._perclos_samples.append((timestamp, dt, closed))
        cutoff = timestamp - self.config.perclos_window_sec
        while self._perclos_samples and self._perclos_samples[0][0] < cutoff:
            self._perclos_samples.popleft()
        total_dt = sum(item[1] for item in self._perclos_samples)
        if total_dt <= 1e-6:
            return 0.0
        closed_dt = sum(item[1] for item in self._perclos_samples if item[2])
        return round((closed_dt / total_dt) * 100.0, 1)
