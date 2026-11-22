"""Command-line interface and main runtime loop for Blink Counter."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .config import AppConfig, DetectorConfig, WellnessConfig
from .detector import BlinkDetector
from .hud import draw_hud
from .logger import SessionLogger
from .web_server import serve_web_app
from .wellness import WellnessMonitor, play_alert_sound


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="blink-counter",
        description=(
            "Cross-platform automatic eye blink counter with EAR auto-calibration, "
            "dry-eye alerts, drowsiness detection, 20-20-20 break timer, and session logging."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the zero-install Browser Web App locally (no OpenCV/MediaPipe required).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for --web mode (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8765, help="Port for --web mode (default: 8765).")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the browser when using --web.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Webcam device index (default: 0).",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Optional path to a video file to analyze instead of a live camera.",
    )
    parser.add_argument("--width", type=int, default=960, help="Requested capture width (default: 960).")
    parser.add_argument("--height", type=int, default=540, help="Requested capture height (default: 540).")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Fixed EAR blink threshold (disables auto-calibration when set, e.g. 0.21).",
    )
    parser.add_argument(
        "--no-calibrate",
        action="store_true",
        help="Skip initial 3-second open-eye auto-calibration.",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "mediapipe", "haar"),
        default="auto",
        help="Vision backend for eye detection (default: auto).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without opening a GUI window (prints live stats to terminal).",
    )
    parser.add_argument("--no-mirror", action="store_true", help="Disable horizontal mirror flip.")
    parser.add_argument("--no-graph", action="store_true", help="Hide the EAR sparkline waveform.")
    parser.add_argument("--no-overlay", action="store_true", help="Hide eye landmark overlays.")
    parser.add_argument(
        "--low-bpm",
        type=float,
        default=10.0,
        help="Dry-eye warning threshold in blinks per minute (default: 10.0).",
    )
    parser.add_argument(
        "--drowsy-seconds",
        type=float,
        default=1.5,
        help="Continuous eye-closure duration in seconds to trigger drowsiness alert (default: 1.5).",
    )
    parser.add_argument(
        "--break-minutes",
        type=float,
        default=20.0,
        help="20-20-20 eye break reminder interval in minutes; 0 disables (default: 20).",
    )
    parser.add_argument("--no-sound", action="store_true", help="Mute audible alerts.")
    parser.add_argument("--no-log", action="store_true", help="Do not save session CSV/JSON logs on exit.")
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Directory to write session CSV/JSON files (default: OS app-data folder).",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> AppConfig:
    """Convert parsed CLI arguments into an :class:`AppConfig` instance."""
    auto_cal = (not args.no_calibrate) and (args.threshold is None)
    detector_cfg = DetectorConfig(
        ear_threshold=args.threshold if args.threshold is not None else 0.21,
        auto_calibrate=auto_cal,
        drowsy_duration_ms=max(200.0, args.drowsy_seconds * 1000.0),
    )
    wellness_cfg = WellnessConfig(
        low_bpm_threshold=max(0.0, args.low_bpm),
        break_interval_sec=max(0.0, args.break_minutes * 60.0),
        enable_break_reminder=args.break_minutes > 0,
        enable_sound=not args.no_sound,
    )
    return AppConfig(
        camera_index=args.camera,
        video_source=args.source,
        frame_width=args.width,
        frame_height=args.height,
        mirror=not args.no_mirror,
        headless=args.headless,
        show_overlay=not args.no_overlay,
        show_graph=not args.no_graph,
        backend=args.backend,
        log_dir=args.log_dir,
        save_logs=not args.no_log,
        web_mode=args.web,
        web_host=args.host,
        web_port=args.port,
        open_browser=not args.no_browser,
        detector=detector_cfg,
        wellness=wellness_cfg,
    )


def run_desktop(config: AppConfig) -> int:
    """Run the OpenCV + MediaPipe desktop (or headless) blink counter."""
    try:
        import cv2
    except ImportError:
        print(
            "[blink-counter] Missing desktop vision dependency (`opencv-python`).\n"
            "Install desktop dependencies with:\n"
            "    pip install -r requirements.txt\n"
            "Or run the zero-install Browser Web App immediately with:\n"
            "    python -m blink_counter --web",
            file=sys.stderr,
        )
        return 1

    from .vision import create_eye_extractor, open_video_capture

    extractor = create_eye_extractor(config.backend)
    cap = open_video_capture(
        camera_index=config.camera_index,
        video_source=config.video_source,
        width=config.frame_width,
        height=config.frame_height,
    )

    detector = BlinkDetector(config.detector)
    wellness = WellnessMonitor(config.wellness)
    logger = SessionLogger(log_dir=config.log_dir)

    muted = not config.wellness.enable_sound
    paused = False
    show_graph = config.show_graph
    show_overlay = config.show_overlay
    last_terminal_print = 0.0
    window_name = "Blink Counter - Eye Wellness Tracker"

    print(
        f"[blink-counter] Started ({extractor.backend_name}). "
        f"{'Headless mode — press Ctrl+C to stop.' if config.headless else 'Press Q or ESC in the window to quit.'}"
    )

    last_analysis = None
    last_wellness = None

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                if config.video_source is not None:
                    print("[blink-counter] Reached end of video file.")
                    break
                print("[blink-counter] Failed to grab frame from camera.", file=sys.stderr)
                break

            if config.mirror and config.video_source is None:
                frame = cv2.flip(frame, 1)

            now = time.monotonic()

            if not paused:
                extraction = extractor.extract(frame)
                if not extraction.face_detected:
                    analysis = detector.update_no_face(now)
                elif extraction.left_eye and extraction.right_eye:
                    analysis = detector.update_from_landmarks(
                        extraction.left_eye, extraction.right_eye, now
                    )
                elif extraction.synthetic_ear is not None:
                    analysis = detector.update_ear(
                        extraction.synthetic_ear, extraction.synthetic_ear, now
                    )
                else:
                    analysis = detector.update_no_face(now)

                snap = wellness.update(now, blink_occurred=analysis.blink_detected)
                last_analysis = analysis
                last_wellness = snap

                if analysis.blink_event is not None:
                    logger.log_blink(analysis.blink_event, snap.current_bpm)

                if not muted:
                    if analysis.drowsy_triggered:
                        play_alert_sound("drowsy")
                    elif snap.dry_eye_triggered or snap.break_status.break_started:
                        play_alert_sound("gentle")
            else:
                extraction = None
                analysis = last_analysis or detector.update_no_face(now)
                snap = last_wellness or wellness.update(now, blink_occurred=False)

            if config.headless:
                if now - last_terminal_print >= 1.0:
                    last_terminal_print = now
                    status = "DROWSY!" if analysis.is_drowsy else ("LOW BPM" if snap.dry_eye_warning else "OK")
                    print(
                        f"\rBlinks: {analysis.total_blinks:4d} | "
                        f"BPM: {snap.current_bpm:5.1f} | "
                        f"EAR: {analysis.smoothed_ear:.3f} (thr {analysis.threshold:.2f}) | "
                        f"PERCLOS: {analysis.perclos:4.1f}% | Status: {status}   ",
                        end="",
                        flush=True,
                    )
            else:
                annotated = draw_hud(
                    frame,
                    analysis,
                    snap,
                    left_eye=extraction.left_eye if extraction else None,
                    right_eye=extraction.right_eye if extraction else None,
                    ear_history=detector.ear_history,
                    show_overlay=show_overlay,
                    show_graph=show_graph,
                    paused=paused,
                    muted=muted,
                    backend_name=extractor.backend_name,
                )
                cv2.imshow(window_name, annotated)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):  # q or ESC
                    break
                if key in (ord("r"), ord("R")):
                    detector.reset(recalibrate=False)
                    wellness.reset(now)
                elif key in (ord("c"), ord("C")):
                    detector.start_calibration()
                elif key in (ord("p"), ord("P")):
                    paused = not paused
                elif key in (ord("m"), ord("M")):
                    muted = not muted
                elif key in (ord("g"), ord("G")):
                    show_graph = not show_graph
                elif key in (ord("o"), ord("O")):
                    show_overlay = not show_overlay
                elif key in (ord("s"), ord("S")):
                    csv_p, json_p = logger.save(
                        duration_sec=snap.elapsed_sec,
                        total_blinks=detector.total_blinks,
                        avg_bpm=snap.avg_bpm,
                        max_bpm=snap.max_bpm,
                        drowsy_events=detector.drowsy_events,
                        dry_eye_alerts=snap.dry_eye_alerts,
                        breaks_completed=snap.break_status.breaks_completed,
                        ear_threshold=detector.threshold,
                        backend=extractor.backend_name,
                    )
                    print(f"\n[blink-counter] Snapshot saved -> {csv_p} & {json_p}")
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        extractor.close()
        if not config.headless:
            cv2.destroyAllWindows()

    if config.headless:
        print()

    final_snap = last_wellness or wellness.update(time.monotonic())
    print(
        f"[blink-counter] Session complete — Total blinks: {detector.total_blinks}, "
        f"Avg BPM: {final_snap.avg_bpm:.1f}, Duration: {final_snap.elapsed_sec:.1f}s"
    )
    if config.save_logs:
        csv_path, json_path = logger.save(
            duration_sec=final_snap.elapsed_sec,
            total_blinks=detector.total_blinks,
            avg_bpm=final_snap.avg_bpm,
            max_bpm=final_snap.max_bpm,
            drowsy_events=detector.drowsy_events,
            dry_eye_alerts=final_snap.dry_eye_alerts,
            breaks_completed=final_snap.break_status.breaks_completed,
            ear_threshold=detector.threshold,
            backend=extractor.backend_name,
        )
        print(f"[blink-counter] Logs saved:\n  CSV : {csv_path}\n  JSON: {json_path}")

    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config = config_from_args(args)
    if config.web_mode:
        return serve_web_app(
            host=config.web_host,
            port=config.web_port,
            open_browser=config.open_browser,
        )
    return run_desktop(config)
