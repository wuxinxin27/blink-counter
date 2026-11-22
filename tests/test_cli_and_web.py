"""Unit tests for CLI argument parsing, cross-platform paths, and the local web server."""

from __future__ import annotations

import threading
import unittest
import urllib.error
import urllib.request

from blink_counter.cli import build_parser, config_from_args
from blink_counter.config import default_cache_dir, default_log_dir
from blink_counter.web_server import create_web_server, locate_web_dir


class TestCliAndWeb(unittest.TestCase):
    def test_cli_defaults_and_overrides(self) -> None:
        parser = build_parser()
        default_cfg = config_from_args(parser.parse_args([]))
        self.assertTrue(default_cfg.detector.auto_calibrate)
        self.assertFalse(default_cfg.web_mode)
        self.assertTrue(default_cfg.wellness.enable_break_reminder)
        self.assertFalse(default_cfg.power.eco_mode)
        self.assertEqual(default_cfg.lang, "auto")

        custom_cfg = config_from_args(
            parser.parse_args(
                [
                    "--camera", "1",
                    "--threshold", "0.19",
                    "--headless",
                    "--low-bpm", "8",
                    "--break-minutes", "0",
                    "--no-sound",
                    "--backend", "haar",
                    "--eco",
                    "--duty-cycle", "60:240",
                    "--lang", "zh",
                ]
            )
        )
        self.assertEqual(custom_cfg.camera_index, 1)
        self.assertAlmostEqual(custom_cfg.detector.ear_threshold, 0.19)
        self.assertFalse(custom_cfg.detector.auto_calibrate)
        self.assertTrue(custom_cfg.headless)
        self.assertFalse(custom_cfg.wellness.enable_break_reminder)
        self.assertFalse(custom_cfg.wellness.enable_sound)
        self.assertEqual(custom_cfg.backend, "haar")
        self.assertTrue(custom_cfg.power.eco_mode)
        self.assertEqual(custom_cfg.frame_width, 480)
        self.assertEqual(custom_cfg.power.target_fps, 15.0)
        self.assertEqual(custom_cfg.power.duty_on_sec, 60.0)
        self.assertEqual(custom_cfg.power.duty_off_sec, 240.0)
        self.assertEqual(custom_cfg.lang, "zh")

    def test_cross_platform_default_dirs(self) -> None:
        self.assertEqual(default_cache_dir().name, "blink-counter")
        self.assertEqual(default_log_dir().name, "sessions")

    def test_web_server_serves_index_and_assets(self) -> None:
        web_dir = locate_web_dir()
        index_path = web_dir / "index.html"
        self.assertTrue(index_path.is_file())
        self.assertTrue((web_dir / "styles.css").is_file())
        self.assertTrue((web_dir / "app.js").is_file())
        html = index_path.read_text(encoding="utf-8")
        self.assertIn("Blink Counter", html)
        self.assertIn("langSelect", html)
        self.assertIn("ecoToggle", html)
        self.assertIn("alertModalBackdrop", html)
        self.assertIn("testAlertBtn", html)

        server = create_web_server(host="127.0.0.1", port=0, web_dir=web_dir)
        port = server.server_address[1]
        self.assertGreater(port, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f"http://127.0.0.1:{port}/index.html", timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                body = resp.read().decode("utf-8")
                self.assertIn("Blink Counter", body)
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, PermissionError):
                self.skipTest("Loopback socket connections are restricted in this environment")
            raise
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
