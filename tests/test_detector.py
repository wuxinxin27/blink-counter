"""Unit tests for EAR computation, BlinkDetector state machine, auto-calibration, and drowsiness."""

from __future__ import annotations

import unittest

from blink_counter.config import DetectorConfig
from blink_counter.detector import BlinkDetector, compute_ear


def _make_eye(width: float = 10.0, height: float = 3.0):
    """Create synthetic 6-point eye coordinates with predictable EAR = height / width."""
    half_h = height / 2.0
    return [
        (0.0, 0.0),           # p1: left corner
        (width * 0.3, -half_h),  # p2: upper-1
        (width * 0.7, -half_h),  # p3: upper-2
        (width, 0.0),         # p4: right corner
        (width * 0.7, half_h),   # p5: lower-2
        (width * 0.3, half_h),   # p6: lower-1
    ]


class TestComputeEar(unittest.TestCase):
    def test_open_and_closed_eye_ratios(self) -> None:
        open_ear = compute_ear(_make_eye(width=10.0, height=3.0))
        closed_ear = compute_ear(_make_eye(width=10.0, height=0.8))
        self.assertAlmostEqual(open_ear, 0.30, places=5)
        self.assertAlmostEqual(closed_ear, 0.08, places=5)
        self.assertGreater(open_ear, closed_ear)

    def test_degenerate_zero_width_returns_zero(self) -> None:
        pts = [(5.0, 5.0)] * 6
        self.assertEqual(compute_ear(pts), 0.0)

    def test_invalid_point_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            compute_ear([(0.0, 0.0)] * 4)


class TestBlinkDetector(unittest.TestCase):
    def test_counts_distinct_blinks_and_ignores_single_frame_glitch(self) -> None:
        cfg = DetectorConfig(
            ear_threshold=0.21,
            hysteresis=0.02,
            smoothing_alpha=1.0,  # disable EMA for deterministic step tests
            min_consec_frames=2,
            min_blink_ms=50.0,
            max_blink_ms=800.0,
            cooldown_ms=140.0,
            auto_calibrate=False,
        )
        detector = BlinkDetector(cfg)

        t = 0.0
        dt = 0.04  # 25 FPS (40 ms/frame)

        # Open eyes baseline
        for _ in range(5):
            res = detector.update_ear(0.32, 0.32, t)
            self.assertFalse(res.blink_detected)
            t += dt

        # Single-frame noise glitch (only 1 frame closed -> should NOT count)
        detector.update_ear(0.14, 0.14, t)
        t += dt
        res = detector.update_ear(0.32, 0.32, t)
        self.assertFalse(res.blink_detected)
        self.assertEqual(detector.total_blinks, 0)
        t += dt

        # Valid blink #1: 3 closed frames (120 ms), then reopen
        for _ in range(3):
            res = detector.update_ear(0.13, 0.14, t)
            self.assertTrue(res.eyes_closed)
            t += dt
        res = detector.update_ear(0.31, 0.32, t)
        self.assertTrue(res.blink_detected)
        self.assertIsNotNone(res.blink_event)
        self.assertEqual(detector.total_blinks, 1)
        assert res.blink_event is not None
        self.assertAlmostEqual(res.blink_event.duration_ms, 120.0, delta=1.0)
        t += 0.30  # past cooldown

        # Valid blink #2 via landmark points
        open_eye = _make_eye(10.0, 3.2)
        closed_eye = _make_eye(10.0, 1.2)
        for _ in range(3):
            detector.update_from_landmarks(closed_eye, closed_eye, t)
            t += dt
        res2 = detector.update_from_landmarks(open_eye, open_eye, t)
        self.assertTrue(res2.blink_detected)
        self.assertEqual(detector.total_blinks, 2)

    def test_auto_calibration_adapts_threshold(self) -> None:
        cfg = DetectorConfig(
            auto_calibrate=True,
            calibration_duration_sec=2.0,
            calibration_ratio=0.72,
            min_auto_threshold=0.14,
            max_auto_threshold=0.28,
            smoothing_alpha=1.0,
        )
        detector = BlinkDetector(cfg)
        t = 0.0
        for _ in range(30):
            res = detector.update_ear(0.34, 0.34, t)
            t += 0.1

        self.assertFalse(res.calibration.active)
        self.assertAlmostEqual(detector.threshold, 0.34 * 0.72, places=3)

    def test_drowsiness_and_perclos(self) -> None:
        cfg = DetectorConfig(
            ear_threshold=0.21,
            smoothing_alpha=1.0,
            drowsy_duration_ms=1000.0,
            auto_calibrate=False,
        )
        detector = BlinkDetector(cfg)

        t = 0.0
        # Open for 1s
        for _ in range(10):
            res = detector.update_ear(0.32, 0.32, t)
            self.assertFalse(res.is_drowsy)
            t += 0.1

        # Closed for 1.5s -> triggers drowsiness once and does not count as a quick blink
        triggered_count = 0
        for _ in range(15):
            res = detector.update_ear(0.11, 0.11, t)
            if res.drowsy_triggered:
                triggered_count += 1
            t += 0.1

        self.assertEqual(triggered_count, 1)
        self.assertTrue(res.is_drowsy)
        self.assertEqual(detector.drowsy_events, 1)
        self.assertGreater(res.perclos, 40.0)

        # Reopen after prolonged closure (> max_blink_ms = 800ms) -> not counted as normal blink
        res_open = detector.update_ear(0.32, 0.32, t)
        self.assertFalse(res_open.blink_detected)
        self.assertEqual(detector.total_blinks, 0)

    def test_no_face_resets_closure_state(self) -> None:
        detector = BlinkDetector(DetectorConfig(auto_calibrate=False, smoothing_alpha=1.0))
        detector.update_ear(0.12, 0.12, 1.0)
        res = detector.update_no_face(1.1)
        self.assertFalse(res.face_detected)
        self.assertFalse(res.eyes_closed)


if __name__ == "__main__":
    unittest.main()
