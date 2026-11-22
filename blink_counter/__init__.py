"""Cross-platform automatic eye blink counter and eye-wellness tracker."""

from __future__ import annotations

__version__ = "1.3.0"

from .config import AppConfig, DetectorConfig, WellnessConfig
from .detector import BlinkDetector, BlinkEvent, CalibrationState, FrameAnalysis, compute_ear
from .i18n import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, Translator, normalize_language
from .logger import SessionLogger
from .power import DutyState, PowerConfig, PowerController, parse_duty_cycle
from .wellness import BreakReminderStatus, WellnessMonitor, WellnessSnapshot

__all__ = [
    "__version__",
    "AppConfig",
    "BlinkDetector",
    "BlinkEvent",
    "BreakReminderStatus",
    "CalibrationState",
    "DetectorConfig",
    "DutyState",
    "FrameAnalysis",
    "LANGUAGE_NAMES",
    "PowerConfig",
    "PowerController",
    "SUPPORTED_LANGUAGES",
    "SessionLogger",
    "Translator",
    "WellnessConfig",
    "WellnessMonitor",
    "WellnessSnapshot",
    "compute_ear",
    "normalize_language",
    "parse_duty_cycle",
]
