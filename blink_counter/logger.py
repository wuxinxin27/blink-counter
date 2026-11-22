"""Session CSV & JSON logger for blink events and eye-wellness summaries."""

from __future__ import annotations

import csv
import json
import platform
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import default_log_dir
from .detector import BlinkEvent


class SessionLogger:
    """Records individual blink events and writes CSV + JSON session reports."""

    def __init__(self, log_dir: Optional[Path] = None, session_id: Optional[str] = None) -> None:
        self.log_dir = Path(log_dir) if log_dir is not None else default_log_dir()
        now = datetime.now(timezone.utc)
        self.started_at_iso = now.isoformat()
        self.session_id = session_id or now.strftime("session_%Y%m%d_%H%M%S")
        self._records: List[Dict[str, Any]] = []
        self._start_ts: Optional[float] = None

    @property
    def records(self) -> List[Dict[str, Any]]:
        return self._records

    def log_blink(self, event: BlinkEvent, current_bpm: float) -> None:
        """Append a blink event to the in-memory session log."""
        if self._start_ts is None:
            self._start_ts = event.timestamp
        elapsed_sec = max(0.0, event.timestamp - self._start_ts)
        self._records.append(
            {
                "blink_index": event.index,
                "iso_time": datetime.now(timezone.utc).isoformat(),
                "elapsed_sec": round(elapsed_sec, 3),
                "duration_ms": event.duration_ms,
                "min_ear": event.min_ear,
                "left_ear": event.left_ear,
                "right_ear": event.right_ear,
                "rolling_bpm": round(current_bpm, 1),
            }
        )

    def build_summary(
        self,
        *,
        duration_sec: float,
        total_blinks: int,
        avg_bpm: float,
        max_bpm: float,
        drowsy_events: int,
        dry_eye_alerts: int,
        breaks_completed: int,
        ear_threshold: float,
        backend: str = "unknown",
    ) -> Dict[str, Any]:
        """Build a structured JSON-serializable session summary dictionary."""
        durations = [float(r["duration_ms"]) for r in self._records]
        if durations:
            duration_stats = {
                "mean_ms": round(statistics.mean(durations), 1),
                "median_ms": round(statistics.median(durations), 1),
                "min_ms": round(min(durations), 1),
                "max_ms": round(max(durations), 1),
            }
        else:
            duration_stats = {
                "mean_ms": 0.0,
                "median_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
            }

        return {
            "session_id": self.session_id,
            "started_at": self.started_at_iso,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "python": platform.python_version(),
                "backend": backend,
            },
            "metrics": {
                "duration_sec": round(duration_sec, 2),
                "total_blinks": total_blinks,
                "avg_bpm": round(avg_bpm, 1),
                "max_bpm": round(max_bpm, 1),
                "drowsy_events": drowsy_events,
                "dry_eye_alerts": dry_eye_alerts,
                "breaks_completed": breaks_completed,
                "ear_threshold": round(ear_threshold, 4),
                "blink_duration": duration_stats,
            },
        }

    def save(
        self,
        *,
        duration_sec: float,
        total_blinks: int,
        avg_bpm: float,
        max_bpm: float,
        drowsy_events: int,
        dry_eye_alerts: int,
        breaks_completed: int,
        ear_threshold: float,
        backend: str = "unknown",
    ) -> Tuple[Path, Path]:
        """Write `<session_id>_blinks.csv` and `<session_id>_summary.json` to disk."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        csv_path = self.log_dir / f"{self.session_id}_blinks.csv"
        json_path = self.log_dir / f"{self.session_id}_summary.json"

        fieldnames = [
            "blink_index",
            "iso_time",
            "elapsed_sec",
            "duration_ms",
            "min_ear",
            "left_ear",
            "right_ear",
            "rolling_bpm",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self._records)

        summary = self.build_summary(
            duration_sec=duration_sec,
            total_blinks=total_blinks,
            avg_bpm=avg_bpm,
            max_bpm=max_bpm,
            drowsy_events=drowsy_events,
            dry_eye_alerts=dry_eye_alerts,
            breaks_completed=breaks_completed,
            ear_threshold=ear_threshold,
            backend=backend,
        )
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return csv_path, json_path
