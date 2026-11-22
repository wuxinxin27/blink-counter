"""Cross-platform automatic eye blink counter and eye-wellness tracker."""

from __future__ import annotations

__version__ = "1.0.0"

from .config import AppConfig, DetectorConfig, WellnessConfig
from .detector import BlinkDetector, BlinkEvent, CalibrationState, FrameAnalysis, compute_ear
from .logger import SessionLogger
from .wellness import BreakReminderStatus, WellnessMonitor, WellnessSnapshot

__all__ = [
    "__version__",
    "AppConfig",
    "BlinkDetector",
    "BlinkEvent",
    "BreakReminderStatus",
    "CalibrationState",
    "DetectorConfig",
    "FrameAnalysis",
    "SessionLogger",
    "WellnessConfig",
    "WellnessMonitor",
    "WellnessSnapshot",
    "compute_ear",
]
