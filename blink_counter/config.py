"""Configuration dataclasses and cross-platform path helpers."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .power import PowerConfig


def default_cache_dir() -> Path:
    """Return an OS-appropriate user cache directory for model files."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "blink-counter"


def default_log_dir() -> Path:
    """Return an OS-appropriate directory for session CSV/JSON logs."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "blink-counter" / "sessions"


@dataclass
class DetectorConfig:
    """Parameters controlling EAR-based blink and drowsiness detection."""

    ear_threshold: float = 0.21
    hysteresis: float = 0.02
    smoothing_alpha: float = 0.45
    min_consec_frames: int = 2
    min_blink_ms: float = 50.0
    max_blink_ms: float = 800.0
    cooldown_ms: float = 140.0
    drowsy_duration_ms: float = 1500.0
    perclos_window_sec: float = 60.0
    auto_calibrate: bool = True
    calibration_duration_sec: float = 3.0
    calibration_ratio: float = 0.72
    min_auto_threshold: float = 0.14
    max_auto_threshold: float = 0.28


@dataclass
class WellnessConfig:
    """Parameters controlling dry-eye monitoring and 20-20-20 break reminders."""

    bpm_window_sec: float = 60.0
    low_bpm_threshold: float = 10.0
    low_bpm_warmup_sec: float = 30.0
    low_bpm_alert_cooldown_sec: float = 45.0
    break_interval_sec: float = 20 * 60.0  # 20 minutes
    break_duration_sec: float = 20.0       # 20 seconds
    enable_break_reminder: bool = True
    enable_sound: bool = True
    enable_popup: bool = True


@dataclass
class AppConfig:
    """Top-level runtime configuration for the desktop / headless / web CLI."""

    camera_index: int = 0
    video_source: Optional[str] = None
    frame_width: int = 640
    frame_height: int = 360
    inference_width: int = 360
    mirror: bool = True
    headless: bool = False
    hide_video: bool = False
    show_overlay: bool = True
    show_graph: bool = True
    backend: str = "auto"  # "auto", "mediapipe", "haar"
    lang: str = "auto"     # "auto", "en", "zh", "ja", "es"
    log_dir: Optional[Path] = None
    save_logs: bool = True
    web_mode: bool = False
    web_host: str = "127.0.0.1"
    web_port: int = 8765
    open_browser: bool = True
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    wellness: WellnessConfig = field(default_factory=WellnessConfig)
    power: PowerConfig = field(default_factory=PowerConfig)
