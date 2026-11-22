"""Command-line interface and power-aware runtime loop for Blink Counter."""

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
from .i18n import SUPPORTED_LANGUAGES, Translator
from .logger import SessionLogger
from .power import PowerConfig, PowerController, parse_duty_cycle
from .web_server import serve_web_app
from .wellness import WellnessMonitor, play_alert_sound


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="blink-counter",
        description=(
            "Cross-platform automatic eye blink counter with Eco power-saving mode, "
            "multi-language UI (en/zh/ja/es), EAR auto-calibration, dry-eye alerts, "
            "drowsiness detection, 20-20-20 break timer, and session logging."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--lang",
        choices=("auto",) + SUPPORTED_LANGUAGES,
        default="auto",
        help="Interface language: auto, en, zh, ja, es (default: auto).",
    )
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
    parser.add_argument("--camera", type=int, default=0, help="Webcam device index (default: 0).")
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Optional path to a video file to analyze instead of a live camera.",
    )
    parser.add_argument("--width", type=int, default=None, help="Capture width (default: 640, eco: 480).")
    parser.add_argument("--height", type=int, default=None, help="Capture height (default: 360, eco: 270).")
    parser.add_argument(
        "--inference-width",
        type=int,
        default=None,
        help="Max frame width passed to the ML detector (default: 360, eco: 280).",
    )
    parser.add_argument(
        "--eco",
        action="store_true",
        help="Enable Eco low-power mode (15 FPS cap, low-res capture, no-face idle backoff, graph off).",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Maximum processing FPS (default: 24, eco: 15).",
    )
    parser.add_argument(
        "--idle-fps",
        type=float,
        default=1.5,
        help="Reduced polling FPS when no face is detected for --idle-after seconds (default: 1.5).",
    )
    parser.add_argument(
        "--idle-after",
        type=float,
        default=5.0,
        help="Seconds with no face before entering low-FPS idle backoff (default: 5.0).",
    )
    parser.add_argument(
        "--no-idle-backoff",
        action="store_true",
        help="Disable automatic FPS reduction when no face is in view.",
    )
    parser.add_argument(
        "--duty-cycle",
        type=str,
        default=None,
        metavar="ON:OFF",
        help=(
            "Periodic wellness sampling in seconds (e.g. 60:240 = monitor 60s, then completely "
            "release the camera for 240s to save battery)."
        ),
    )
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
        help="Run without opening a GUI window (lowest UI power; prints live stats to terminal).",
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
    eco = bool(args.eco)
    width = args.width if args.width is not None else (480 if eco else 640)
    height = args.height if args.height is not None else (270 if eco else 360)
    inf_width = args.inference_width if args.inference_width is not None else (280 if eco else 360)
    target_fps = args.fps if args.fps is not None else (15.0 if eco else 24.0)
    duty_on, duty_off = parse_duty_cycle(args.duty_cycle)

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
    power_cfg = PowerConfig(
        eco_mode=eco,
        target_fps=max(1.0, target_fps),
        eco_fps=min(15.0, max(1.0, args.fps)) if args.fps is not None else 15.0,
        idle_backoff=not args.no_idle_backoff,
        idle_after_sec=max(1.0, args.idle_after),
        idle_fps=max(0.5, args.idle_fps),
        duty_on_sec=duty_on,
        duty_off_sec=duty_off,
    )
    return AppConfig(
        camera_index=args.camera,
        video_source=args.source,
        frame_width=width,
        frame_height=height,
        inference_width=inf_width,
        mirror=not args.no_mirror,
        headless=args.headless,
        show_overlay=not args.no_overlay,
        show_graph=(not args.no_graph) and (not eco),
        backend=args.backend,
        lang=args.lang,
        log_dir=args.log_dir,
        save_logs=not args.no_log,
        web_mode=args.web,
        web_host=args.host,
        web_port=args.port,
        open_browser=not args.no_browser,
        detector=detector_cfg,
        wellness=wellness_cfg,
        power=power_cfg,
    )


def run_desktop(config: AppConfig) -> int:
    """Run the power-aware OpenCV + MediaPipe desktop (or headless) blink counter."""
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

    tr = Translator(config.lang)
    power = PowerController(config.power)
    extractor = create_eye_extractor(config.backend, inference_width=config.inference_width)

    def _open_cam():
        return open_video_capture(
            camera_index=config.camera_index,
            video_source=config.video_source,
            width=config.frame_width,
            height=config.frame_height,
            fps=config.power.eco_fps if config.power.eco_mode else config.power.target_fps,
        )

    cap = _open_cam()
    detector = BlinkDetector(config.detector)
    wellness = WellnessMonitor(config.wellness)
    logger = SessionLogger(log_dir=config.log_dir)

    muted = not config.wellness.enable_sound
    paused = False
    show_graph = config.show_graph
    show_overlay = config.show_overlay
    last_terminal_print = 0.0
    window_name = "Blink Counter"
    in_duty_sleep = False

    mode_label = tr.t("mode_eco") if power.eco_mode else tr.t("mode_standard")
    hint = tr.t("hint_headless") if config.headless else tr.t("hint_window")
    print(tr.t("started_msg", backend=extractor.backend_name, lang=tr.language_name, mode=mode_label, hint=hint))

    last_analysis = None
    last_wellness = None
    last_extraction = None
    last_annotated = None
    power.reset(time.monotonic())

    try:
        while True:
            now = time.monotonic()

            # Handle duty-cycle camera sleep (only for live webcam, not video files)
            if config.video_source is None:
                duty = power.duty_state(now)
                if duty.enabled and not duty.camera_active:
                    if not in_duty_sleep:
                        in_duty_sleep = True
                        if cap is not None:
                            cap.release()
                            cap = None
                        if not config.headless:
                            cv2.destroyAllWindows()
                        print("\n" + tr.t("duty_sleep_msg", sec=int(round(duty.phase_remaining_sec))))
                    if config.headless and now - last_terminal_print >= 1.0:
                        last_terminal_print = now
                        print(
                            f"\r{tr.t('status_sleep', sec=int(round(duty.phase_remaining_sec)))}   ",
                            end="",
                            flush=True,
                        )
                    time.sleep(min(0.5, max(0.05, duty.phase_remaining_sec)))
                    continue
                if in_duty_sleep and duty.camera_active:
                    in_duty_sleep = False
                    print("\n" + tr.t("duty_wake_msg", sec=int(round(duty.phase_remaining_sec))))
                    cap = _open_cam()

            # Frame-rate pacing to avoid redundant inference and CPU wakeups
            if config.video_source is None and not power.should_process(now):
                sleep_s = power.recommended_sleep_sec(now)
                if config.headless:
                    time.sleep(max(0.005, sleep_s))
                    continue
                wait_ms = max(1, min(33, int(sleep_s * 1000)))
                key = cv2.waitKey(wait_ms) & 0xFF
                if key != 255:
                    action = _handle_hotkey(
                        key,
                        now=now,
                        detector=detector,
                        wellness=wellness,
                        power=power,
                        translator=tr,
                        logger=logger,
                        snap=last_wellness,
                        backend_name=extractor.backend_name,
                        state={"paused": paused, "muted": muted, "show_graph": show_graph, "show_overlay": show_overlay},
                    )
                    if action == "quit":
                        break
                    paused = action["paused"]
                    muted = action["muted"]
                    show_graph = action["show_graph"]
                    show_overlay = action["show_overlay"]
                continue

            assert cap is not None
            ok, frame = cap.read()
            if not ok:
                if config.video_source is not None:
                    break
                print("[blink-counter] Failed to grab frame from camera.", file=sys.stderr)
                break

            if config.mirror and config.video_source is None:
                frame = cv2.flip(frame, 1)

            if not paused:
                extraction = extractor.extract(frame, timestamp_ms=int(now * 1000))
                last_extraction = extraction
                power.note_face_seen(now, extraction.face_detected)

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
                extraction = last_extraction
                analysis = last_analysis or detector.update_no_face(now)
                snap = last_wellness or wellness.update(now, blink_occurred=False)

            eff_fps = power.effective_fps(now)
            idle_now = power.is_idle(now)

            if config.headless:
                if now - last_terminal_print >= 1.0:
                    last_terminal_print = now
                    if analysis.is_drowsy:
                        status_txt = tr.t("status_drowsy")
                    elif idle_now:
                        status_txt = tr.t("status_idle")
                    elif snap.dry_eye_warning:
                        status_txt = tr.t("status_low_bpm")
                    else:
                        status_txt = tr.t("status_ok")
                    line = tr.t(
                        "terminal_line",
                        blinks=analysis.total_blinks,
                        bpm=snap.current_bpm,
                        ear=analysis.smoothed_ear,
                        thr=analysis.threshold,
                        perclos=analysis.perclos,
                        fps=eff_fps,
                        status=status_txt,
                    )
                    print(f"\r{line}   ", end="", flush=True)
            else:
                last_annotated = draw_hud(
                    frame,
                    analysis,
                    snap,
                    translator=tr,
                    left_eye=extraction.left_eye if extraction else None,
                    right_eye=extraction.right_eye if extraction else None,
                    ear_history=detector.ear_history,
                    show_overlay=show_overlay,
                    show_graph=show_graph,
                    paused=paused,
                    muted=muted,
                    eco_mode=power.eco_mode,
                    idle_mode=idle_now,
                    effective_fps=eff_fps,
                    backend_name=extractor.backend_name,
                )
                cv2.imshow(window_name, last_annotated)
                key = cv2.waitKey(1) & 0xFF
                if key != 255:
                    action = _handle_hotkey(
                        key,
                        now=now,
                        detector=detector,
                        wellness=wellness,
                        power=power,
                        translator=tr,
                        logger=logger,
                        snap=snap,
                        backend_name=extractor.backend_name,
                        state={"paused": paused, "muted": muted, "show_graph": show_graph, "show_overlay": show_overlay},
                    )
                    if action == "quit":
                        break
                    paused = action["paused"]
                    muted = action["muted"]
                    show_graph = action["show_graph"]
                    show_overlay = action["show_overlay"]
    except KeyboardInterrupt:
        pass
    finally:
        if cap is not None:
            cap.release()
        extractor.close()
        if not config.headless:
            cv2.destroyAllWindows()

    if config.headless:
        print()

    final_snap = last_wellness or wellness.update(time.monotonic())
    print(
        tr.t(
            "session_complete",
            blinks=detector.total_blinks,
            bpm=final_snap.avg_bpm,
            dur=final_snap.elapsed_sec,
        )
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
        print(tr.t("logs_saved", csv=csv_path, json=json_path))

    return 0


def _handle_hotkey(
    key: int,
    *,
    now: float,
    detector: BlinkDetector,
    wellness: WellnessMonitor,
    power: PowerController,
    translator: Translator,
    logger: SessionLogger,
    snap,
    backend_name: str,
    state: dict,
):
    if key in (ord("q"), ord("Q"), 27):
        return "quit"
    if key in (ord("r"), ord("R")):
        detector.reset(recalibrate=False)
        wellness.reset(now)
    elif key in (ord("c"), ord("C")):
        detector.start_calibration()
    elif key in (ord("p"), ord("P")):
        state["paused"] = not state["paused"]
    elif key in (ord("m"), ord("M")):
        state["muted"] = not state["muted"]
    elif key in (ord("g"), ord("G")):
        state["show_graph"] = not state["show_graph"]
    elif key in (ord("o"), ord("O")):
        state["show_overlay"] = not state["show_overlay"]
    elif key in (ord("e"), ord("E")):
        eco_now = power.toggle_eco_mode()
        if eco_now:
            state["show_graph"] = False
    elif key in (ord("l"), ord("L")):
        translator.cycle_language()
    elif key in (ord("s"), ord("S")) and snap is not None:
        csv_p, json_p = logger.save(
            duration_sec=snap.elapsed_sec,
            total_blinks=detector.total_blinks,
            avg_bpm=snap.avg_bpm,
            max_bpm=snap.max_bpm,
            drowsy_events=detector.drowsy_events,
            dry_eye_alerts=snap.dry_eye_alerts,
            breaks_completed=snap.break_status.breaks_completed,
            ear_threshold=detector.threshold,
            backend=backend_name,
        )
        print("\n" + translator.t("snapshot_saved", csv=csv_p, json=json_p))
    return state


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
            lang=config.lang,
        )
    return run_desktop(config)
