"""Unit tests for PowerController (Eco mode, idle backoff, duty cycling) and i18n translations."""

from __future__ import annotations

import unittest

from blink_counter.i18n import (
    LANGUAGE_NAMES,
    SUPPORTED_LANGUAGES,
    TRANSLATIONS,
    Translator,
    normalize_language,
)
from blink_counter.power import PowerConfig, PowerController, parse_duty_cycle


class TestPowerController(unittest.TestCase):
    def test_fps_pacing_and_eco_toggle(self) -> None:
        ctrl = PowerController(PowerConfig(eco_mode=False, target_fps=20.0, eco_fps=10.0, idle_backoff=False))
        self.assertEqual(ctrl.effective_fps(0.0), 20.0)
        self.assertTrue(ctrl.should_process(0.0))
        self.assertFalse(ctrl.should_process(0.02))  # < 0.05s
        self.assertTrue(ctrl.should_process(0.055))  # >= 0.05s

        # Toggle Eco mode -> cap drops to 10 FPS (0.10s interval)
        self.assertTrue(ctrl.toggle_eco_mode())
        self.assertEqual(ctrl.effective_fps(0.055), 10.0)
        self.assertFalse(ctrl.should_process(0.10))
        self.assertTrue(ctrl.should_process(0.16))

    def test_no_face_idle_backoff_and_recovery(self) -> None:
        ctrl = PowerController(
            PowerConfig(eco_mode=True, eco_fps=15.0, idle_backoff=True, idle_after_sec=5.0, idle_fps=1.5)
        )
        ctrl.note_face_seen(0.0, True)
        self.assertFalse(ctrl.is_idle(4.0))
        self.assertEqual(ctrl.effective_fps(4.0), 15.0)

        # After 5s without a face -> enters 1.5 FPS idle backoff
        ctrl.note_face_seen(5.5, False)
        self.assertTrue(ctrl.is_idle(5.5))
        self.assertEqual(ctrl.effective_fps(5.5), 1.5)

        # Face returns -> immediately restores 15 FPS
        ctrl.note_face_seen(6.0, True)
        self.assertFalse(ctrl.is_idle(6.0))
        self.assertEqual(ctrl.effective_fps(6.0), 15.0)

    def test_duty_cycle_camera_on_off_phases(self) -> None:
        on_s, off_s = parse_duty_cycle("60:240")
        self.assertEqual((on_s, off_s), (60.0, 240.0))

        ctrl = PowerController(PowerConfig(duty_on_sec=on_s, duty_off_sec=off_s))
        s0 = ctrl.duty_state(100.0)
        self.assertTrue(s0.enabled)
        self.assertTrue(s0.camera_active)
        self.assertAlmostEqual(s0.phase_remaining_sec, 60.0)

        s_sleep = ctrl.duty_state(170.0)  # 70s elapsed -> 10s into sleep phase
        self.assertFalse(s_sleep.camera_active)
        self.assertAlmostEqual(s_sleep.phase_remaining_sec, 230.0)

        s_wake = ctrl.duty_state(405.0)   # 305s elapsed -> 5s into next active cycle
        self.assertTrue(s_wake.camera_active)
        self.assertAlmostEqual(s_wake.phase_remaining_sec, 55.0)

    def test_invalid_duty_cycle_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_duty_cycle("60")
        with self.assertRaises(ValueError):
            parse_duty_cycle("0:120")


class TestI18n(unittest.TestCase):
    def test_all_languages_have_complete_keys(self) -> None:
        en_keys = set(TRANSLATIONS["en"].keys())
        for lang in SUPPORTED_LANGUAGES:
            self.assertIn(lang, LANGUAGE_NAMES)
            self.assertEqual(set(TRANSLATIONS[lang].keys()), en_keys, f"Key mismatch in language {lang}")

    def test_translator_normalization_and_cycling(self) -> None:
        self.assertEqual(normalize_language("zh-CN"), "zh")
        self.assertEqual(normalize_language("ja_JP.UTF-8"), "ja")
        self.assertEqual(normalize_language("es-ES"), "es")

        with self.assertRaises(ValueError):
            normalize_language("xx")

        tr = Translator("en")
        self.assertEqual(tr.t("blinks"), "BLINKS")
        seen = [tr.lang]
        for _ in range(len(SUPPORTED_LANGUAGES)):
            seen.append(tr.cycle_language())
        self.assertEqual(seen[0], seen[-1])
        self.assertEqual(set(seen), set(SUPPORTED_LANGUAGES))

        tr.set_language("zh")
        self.assertEqual(tr.t("blinks"), "眨眼次数")
        self.assertIn("50%", tr.t("calibrating_banner", pct=50))


if __name__ == "__main__":
    unittest.main()
