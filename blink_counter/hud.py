"""Live OpenCV HUD overlay and real-time EAR sparkline chart."""

from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple

from .detector import FrameAnalysis, Point2D
from .wellness import WellnessSnapshot


def _format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def draw_hud(
    frame: Any,
    analysis: FrameAnalysis,
    wellness: WellnessSnapshot,
    *,
    left_eye: Optional[Sequence[Point2D]] = None,
    right_eye: Optional[Sequence[Point2D]] = None,
    ear_history: Sequence[Tuple[float, float]] = (),
    show_overlay: bool = True,
    show_graph: bool = True,
    paused: bool = False,
    muted: bool = False,
    backend_name: str = "",
) -> Any:
    """Render live metrics, eye contours, alert banners, and EAR waveform onto `frame`."""
    import cv2
    import numpy as np

    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX

    # 1. Draw eye landmark contours
    if show_overlay and analysis.face_detected:
        eye_color = (82, 95, 255) if analysis.eyes_closed else (110, 235, 145)
        for eye_pts in (left_eye, right_eye):
            if eye_pts and len(eye_pts) == 6:
                pts = np.array([(int(x), int(y)) for x, y in eye_pts], dtype=np.int32)
                cv2.polylines(frame, [pts], isClosed=True, color=eye_color, thickness=2, lineType=cv2.LINE_AA)
                for px, py in pts:
                    cv2.circle(frame, (int(px), int(py)), 2, (255, 255, 255), -1, lineType=cv2.LINE_AA)

    # 2. Top translucent status panel
    overlay = frame.copy()
    panel_h = 84
    cv2.rectangle(overlay, (0, 0), (w, panel_h), (18, 22, 32), -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

    # Blink count
    cv2.putText(frame, "BLINKS", (18, 24), font, 0.48, (150, 165, 190), 1, cv2.LINE_AA)
    cv2.putText(frame, str(analysis.total_blinks), (18, 66), font, 1.35, (110, 235, 175), 3, cv2.LINE_AA)

    # Live BPM
    bpm_color = (70, 195, 255) if not wellness.dry_eye_warning else (60, 185, 255)
    if wellness.dry_eye_warning:
        bpm_color = (60, 165, 255)  # warm amber in BGR
    cv2.putText(frame, "RATE (BPM)", (155, 24), font, 0.48, (150, 165, 190), 1, cv2.LINE_AA)
    cv2.putText(frame, f"{wellness.current_bpm:4.1f}", (155, 62), font, 1.0, bpm_color, 2, cv2.LINE_AA)

    # EAR & threshold
    ear_color = (82, 95, 255) if analysis.eyes_closed else (235, 240, 248)
    cv2.putText(
        frame,
        f"EAR (THR {analysis.threshold:.2f})",
        (300, 24),
        font,
        0.48,
        (150, 165, 190),
        1,
        cv2.LINE_AA,
    )
    ear_text = f"{analysis.smoothed_ear:.3f}" if analysis.face_detected else "NO FACE"
    cv2.putText(frame, ear_text, (300, 62), font, 0.95, ear_color, 2, cv2.LINE_AA)

    # Session time & 20-20-20 timer
    cv2.putText(frame, "SESSION", (485, 24), font, 0.48, (150, 165, 190), 1, cv2.LINE_AA)
    cv2.putText(
        frame,
        _format_duration(wellness.elapsed_sec),
        (485, 62),
        font,
        0.9,
        (230, 235, 245),
        2,
        cv2.LINE_AA,
    )

    if w >= 720 and wellness.break_status.enabled:
        cv2.putText(frame, "NEXT BREAK", (625, 24), font, 0.48, (150, 165, 190), 1, cv2.LINE_AA)
        b_text = (
            f"BREAK {int(wellness.break_status.break_seconds_remaining)}s"
            if wellness.break_status.in_break
            else _format_duration(wellness.break_status.seconds_until_next_break)
        )
        cv2.putText(frame, b_text, (625, 62), font, 0.85, (140, 230, 220), 2, cv2.LINE_AA)

    # Status pill on top-right
    status_label = "MUTED" if muted else "SOUND ON"
    if paused:
        status_label = "PAUSED"
    cv2.putText(frame, status_label, (max(w - 130, 10), 28), font, 0.5, (180, 195, 220), 1, cv2.LINE_AA)
    if backend_name:
        cv2.putText(frame, backend_name, (max(w - 175, 10), 56), font, 0.42, (125, 140, 165), 1, cv2.LINE_AA)

    # 3. Alert / status banners below top panel
    banner_y = panel_h + 12
    if analysis.calibration.active:
        pct = int(analysis.calibration.progress * 100)
        _draw_banner(
            frame,
            banner_y,
            f"Calibrating open-eye baseline... look naturally at the screen ({pct}%)",
            (180, 125, 45),
        )
        banner_y += 42
    elif analysis.is_drowsy:
        _draw_banner(
            frame,
            banner_y,
            f"DROWSINESS ALERT! Eyes closed for {analysis.closure_duration_ms / 1000.0:.1f}s",
            (45, 50, 215),
        )
        banner_y += 42
    elif wellness.break_status.in_break:
        rem = int(wellness.break_status.break_seconds_remaining)
        _draw_banner(
            frame,
            banner_y,
            f"20-20-20 EYE BREAK: Look 20 ft (6 m) away for {rem}s",
            (145, 130, 35),
        )
        banner_y += 42
    elif wellness.dry_eye_warning:
        _draw_banner(
            frame,
            banner_y,
            f"LOW BLINK RATE ({wellness.current_bpm:.1f} BPM) - Remember to blink to prevent dry eyes!",
            (35, 125, 210),
        )
        banner_y += 42

    # 4. Real-time EAR waveform graph (bottom-right)
    if show_graph and len(ear_history) >= 2 and w >= 480 and h >= 260:
        gw, gh = 260, 96
        gx, gy = w - gw - 16, h - gh - 42
        g_overlay = frame.copy()
        cv2.rectangle(g_overlay, (gx, gy), (gx + gw, gy + gh), (18, 22, 32), -1)
        cv2.addWeighted(g_overlay, 0.78, frame, 0.22, 0, frame)
        cv2.rectangle(frame, (gx, gy), (gx + gw, gy + gh), (65, 78, 102), 1)

        ear_min, ear_max = 0.08, 0.42
        def _to_y(val: float) -> int:
            norm = (val - ear_min) / (ear_max - ear_min)
            norm = max(0.0, min(1.0, norm))
            return int(gy + gh - 8 - norm * (gh - 20))

        # Threshold line
        ty = _to_y(analysis.threshold)
        cv2.line(frame, (gx + 4, ty), (gx + gw - 4, ty), (70, 175, 255), 1, cv2.LINE_AA)

        recent = list(ear_history)[-120:]
        n = len(recent)
        pts = []
        for idx, (_, ear_val) in enumerate(recent):
            px = int(gx + 6 + (idx / max(1, n - 1)) * (gw - 12))
            py = _to_y(ear_val)
            pts.append((px, py))
        if len(pts) >= 2:
            arr = np.array(pts, dtype=np.int32)
            cv2.polylines(frame, [arr], isClosed=False, color=(110, 235, 175), thickness=2, lineType=cv2.LINE_AA)

        cv2.putText(frame, "EAR Waveform", (gx + 8, gy + 15), font, 0.4, (175, 190, 210), 1, cv2.LINE_AA)

    # 5. Bottom hotkey bar
    footer = frame.copy()
    cv2.rectangle(footer, (0, h - 30), (w, h), (18, 22, 32), -1)
    cv2.addWeighted(footer, 0.78, frame, 0.22, 0, frame)
    help_text = "[Q] Quit  [R] Reset  [C] Calibrate  [P] Pause  [M] Mute  [G] Graph  [S] Save"
    cv2.putText(frame, help_text, (14, h - 10), font, 0.44, (175, 190, 210), 1, cv2.LINE_AA)

    return frame


def _draw_banner(frame: Any, y: int, text: str, bgr_color: Tuple[int, int, int]) -> None:
    import cv2

    w = frame.shape[1]
    overlay = frame.copy()
    cv2.rectangle(overlay, (16, y), (w - 16, y + 34), bgr_color, -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    cv2.putText(
        frame,
        text,
        (28, y + 23),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
