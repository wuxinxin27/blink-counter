"""Unit tests for WellnessMonitor (BPM, dry-eye alerts, and 20-20-20 break timer)."""

from __future__ import annotations

import unittest

from blink_counter.config import WellnessConfig
from blink_counter.wellness import WellnessMonitor


class TestWellnessMonitor(unittest.TestCase):
    def test_rolling_bpm_and_dry_eye_alert(self) -> None:
        cfg = WellnessConfig(
            bpm_window_sec=60.0,
            low_bpm_threshold=10.0,
            low_bpm_warmup_sec=20.0,
            low_bpm_alert_cooldown_sec=30.0,
            enable_break_reminder=False,
        )
        monitor = WellnessMonitor(cfg)

        # Start at t=0, simulate 15 blinks over 60 seconds -> 15 BPM (healthy)
        monitor.update(0.0)
        for i in range(1, 16):
            snap = monitor.update(i * 4.0, blink_occurred=True)
        self.assertAlmostEqual(snap.current_bpm, 15.0, delta=1.0)
        self.assertFalse(snap.dry_eye_warning)

        # Stop blinking for 65 seconds -> BPM drops to 0 -> triggers dry-eye alert
        snap_low = monitor.update(125.0, blink_occurred=False)
        self.assertEqual(snap_low.current_bpm, 0.0)
        self.assertTrue(snap_low.dry_eye_warning)
        self.assertTrue(snap_low.dry_eye_triggered)
        self.assertEqual(snap_low.dry_eye_alerts, 1)

        # Within cooldown -> warning still active, but not re-triggered
        snap_cooldown = monitor.update(135.0, blink_occurred=False)
        self.assertTrue(snap_cooldown.dry_eye_warning)
        self.assertFalse(snap_cooldown.dry_eye_triggered)
        self.assertEqual(snap_cooldown.dry_eye_alerts, 1)

    def test_20_20_20_break_lifecycle(self) -> None:
        cfg = WellnessConfig(
            break_interval_sec=60.0,
            break_duration_sec=20.0,
            enable_break_reminder=True,
        )
        monitor = WellnessMonitor(cfg)

        s0 = monitor.update(100.0)
        self.assertFalse(s0.break_status.in_break)
        self.assertAlmostEqual(s0.break_status.seconds_until_next_break, 60.0)

        # At t=160 -> break begins
        s_start = monitor.update(160.0)
        self.assertTrue(s_start.break_status.in_break)
        self.assertTrue(s_start.break_status.break_started)
        self.assertAlmostEqual(s_start.break_status.break_seconds_remaining, 20.0)

        # Midway through break
        s_mid = monitor.update(170.0)
        self.assertTrue(s_mid.break_status.in_break)
        self.assertAlmostEqual(s_mid.break_status.break_seconds_remaining, 10.0)

        # Break finishes at t=180
        s_done = monitor.update(180.0)
        self.assertFalse(s_done.break_status.in_break)
        self.assertTrue(s_done.break_status.break_completed)
        self.assertEqual(s_done.break_status.breaks_completed, 1)


if __name__ == "__main__":
    unittest.main()
