"""Unit tests for SessionLogger CSV and JSON output."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from blink_counter.detector import BlinkEvent
from blink_counter.logger import SessionLogger


class TestSessionLogger(unittest.TestCase):
    def test_save_csv_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(log_dir=Path(tmpdir), session_id="test_session")
            logger.log_blink(
                BlinkEvent(
                    index=1,
                    timestamp=10.0,
                    duration_ms=145.0,
                    min_ear=0.14,
                    left_ear=0.13,
                    right_ear=0.15,
                ),
                current_bpm=14.0,
            )
            logger.log_blink(
                BlinkEvent(
                    index=2,
                    timestamp=14.5,
                    duration_ms=175.0,
                    min_ear=0.12,
                    left_ear=0.12,
                    right_ear=0.12,
                ),
                current_bpm=16.0,
            )

            csv_path, json_path = logger.save(
                duration_sec=30.0,
                total_blinks=2,
                avg_bpm=4.0,
                max_bpm=16.0,
                drowsy_events=0,
                dry_eye_alerts=1,
                breaks_completed=0,
                ear_threshold=0.21,
                backend="mediapipe-facemesh",
            )

            self.assertTrue(csv_path.is_file())
            self.assertTrue(json_path.is_file())

            with csv_path.open("r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["blink_index"], "1")
            self.assertEqual(rows[1]["duration_ms"], "175.0")

            with json_path.open("r", encoding="utf-8") as f:
                summary = json.load(f)
            self.assertEqual(summary["session_id"], "test_session")
            self.assertEqual(summary["metrics"]["total_blinks"], 2)
            self.assertEqual(summary["metrics"]["blink_duration"]["mean_ms"], 160.0)
            self.assertEqual(summary["platform"]["backend"], "mediapipe-facemesh")


if __name__ == "__main__":
    unittest.main()
