"""Low-overhead OpenCV HUD with ROI-only blending, real-time EAR graph, and Unicode/CJK i18n."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Any, List, Optional, Sequence, Tuple

from .detector import FrameAnalysis, Point2D
from .i18n import Translator
from .wellness import WellnessSnapshot


def _format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def _blend_rect(
    frame: Any,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    bgr_color: Tuple[int, int, int],
    alpha: float,
) -> None:
    """Alpha-blend a solid rectangle directly into the ROI slice (no full-frame copy)."""
    import cv2
    import numpy as np

    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    color_patch = np.empty_like(roi)
    color_patch[:] = bgr_color
    cv2.addWeighted(color_patch, alpha, roi, 1.0 - alpha, 0, dst=roi)


@lru_cache(maxsize=1)
def _find_unicode_font_path() -> Optional[str]:
    """Locate a cross-platform system font capable of rendering Latin + CJK glyphs."""
    candidates: List[str] = []
    if sys.platform == "darwin":
        candidates.extend(
            [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/System/Library/Fonts/STHeiti Medium.ttc",
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            ]
        )
    elif sys.platform == "win32":
        win_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        candidates.extend(
            [
                os.path.join(win_fonts, "msyh.ttc"),
                os.path.join(win_fonts, "simhei.ttf"),
                os.path.join(win_fonts, "meiryo.ttc"),
                os.path.join(win_fonts, "segoeui.ttf"),
            ]
        )
    else:
        candidates.extend(
            [
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        )

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


@lru_cache(maxsize=16)
def _load_pil_font(font_path: str, size: int) -> Any:
    from PIL import ImageFont

    return ImageFont.truetype(font_path, size=size)


def _can_render_unicode() -> bool:
    if _find_unicode_font_path() is None:
        return False
    try:
        import PIL.Image  # noqa: F401
        import PIL.ImageDraw  # noqa: F401
        import PIL.ImageFont  # noqa: F401
        return True
    except ImportError:
        return False


def _draw_text_batch(
    frame: Any,
    items: Sequence[Tuple[str, Tuple[int, int], float, Tuple[int, int, int], int]],
    use_unicode: bool,
) -> None:
    """Draw a batch of text items using either fast cv2.putText or Pillow Unicode rendering."""
    import cv2

    if not items:
        return

    if not use_unicode:
        font = cv2.FONT_HERSHEY_SIMPLEX
        for text, (x, y), scale, bgr, thickness in items:
            cv2.putText(frame, text, (x, y), font, scale, bgr, thickness, cv2.LINE_AA)
        return

    import numpy as np
    from PIL import Image, ImageDraw

    font_path = _find_unicode_font_path()
    assert font_path is not None
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil_img)

    for text, (x, y), scale, (b, g, r), _ in items:
        px_size = max(11, int(round(scale * 26)))
        pil_font = _load_pil_font(font_path, px_size)
        # cv2 uses baseline y; adjust upward so Pillow top-left positioning aligns cleanly
        draw.text((x, max(0, y - int(px_size * 0.85))), text, font=pil_font, fill=(r, g, b))

    frame[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)


def draw_hud(
    frame: Any,
    analysis: FrameAnalysis,
    wellness: WellnessSnapshot,
    *,
    translator: Optional[Translator] = None,
    left_eye: Optional[Sequence[Point2D]] = None,
    right_eye: Optional[Sequence[Point2D]] = None,
    ear_history: Sequence[Tuple[float, float]] = (),
    show_overlay: bool = True,
    show_graph: bool = True,
    paused: bool = False,
    muted: bool = False,
    eco_mode: bool = False,
    idle_mode: bool = False,
    effective_fps: float = 30.0,
    backend_name: str = "",
) -> Any:
    """Render live metrics, eye contours, alert banners, and EAR waveform onto `frame`."""
    import cv2
    import numpy as np

    tr = translator or Translator("en")
    needs_unicode = tr.lang != "en"
    unicode_ready = _can_render_unicode() if needs_unicode else False
    # If Pillow/CJK font is absent, fall back to English on the OpenCV canvas to avoid '????'
    canvas_tr = tr if (tr.lang == "en" or unicode_ready) else Translator("en")

    h, w = frame.shape[:2]
    text_items: List[Tuple[str, Tuple[int, int], float, Tuple[int, int, int], int]] = []

    # 1. Eye landmark contours
    if show_overlay and analysis.face_detected:
        eye_color = (82, 95, 255) if analysis.eyes_closed else (110, 235, 145)
        for eye_pts in (left_eye, right_eye):
            if eye_pts and len(eye_pts) == 6:
                pts = np.array([(int(x), int(y)) for x, y in eye_pts], dtype=np.int32)
                cv2.polylines(frame, [pts], isClosed=True, color=eye_color, thickness=2, lineType=cv2.LINE_AA)
                for px, py in pts:
                    cv2.circle(frame, (int(px), int(py)), 2, (255, 255, 255), -1, lineType=cv2.LINE_AA)

    # 2. Top translucent status panel (ROI-only blend, zero full-frame copy)
    panel_h = 80
    _blend_rect(frame, 0, 0, w, panel_h, (18, 22, 32), 0.78)

    text_items.append((canvas_tr.t("blinks"), (16, 23), 0.48, (150, 165, 190), 1))
    text_items.append((str(analysis.total_blinks), (16, 64), 1.30, (110, 235, 175), 3))

    bpm_color = (60, 165, 255) if wellness.dry_eye_warning else (70, 195, 255)
    text_items.append((canvas_tr.t("rate_bpm"), (135, 23), 0.46, (150, 165, 190), 1))
    text_items.append((f"{wellness.current_bpm:4.1f}", (135, 60), 0.95, bpm_color, 2))

    ear_color = (82, 95, 255) if analysis.eyes_closed else (235, 240, 248)
    text_items.append((canvas_tr.t("ear_thr", thr=analysis.threshold), (265, 23), 0.46, (150, 165, 190), 1))
    ear_text = f"{analysis.smoothed_ear:.3f}" if analysis.face_detected else canvas_tr.t("no_face")
    text_items.append((ear_text, (265, 60), 0.88, ear_color, 2))

    if w >= 520:
        text_items.append((canvas_tr.t("session"), (420, 23), 0.46, (150, 165, 190), 1))
        text_items.append((_format_duration(wellness.elapsed_sec), (420, 60), 0.84, (230, 235, 245), 2))

    if w >= 660 and wellness.break_status.enabled:
        text_items.append((canvas_tr.t("next_break"), (535, 23), 0.46, (150, 165, 190), 1))
        b_text = (
            canvas_tr.t("break_short", sec=int(wellness.break_status.break_seconds_remaining))
            if wellness.break_status.in_break
            else _format_duration(wellness.break_status.seconds_until_next_break)
        )
        text_items.append((b_text, (535, 60), 0.78, (140, 230, 220), 2))

    # Top-right status + Eco/Idle badge
    status_label = canvas_tr.t("paused") if paused else (
        canvas_tr.t("muted") if muted else canvas_tr.t("sound_on")
    )
    text_items.append((status_label, (max(w - 132, 10), 24), 0.46, (185, 200, 225), 1))

    if idle_mode:
        power_label = canvas_tr.t("idle_badge", fps=effective_fps)
        power_color = (70, 210, 255)
    elif eco_mode:
        power_label = canvas_tr.t("eco_badge", fps=effective_fps)
        power_color = (120, 235, 160)
    else:
        power_label = f"{canvas_tr.language_name}" if backend_name else ""
        power_color = (135, 155, 180)
    if power_label:
        text_items.append((power_label, (max(w - 132, 10), 50), 0.44, power_color, 1))
    if backend_name and w >= 720:
        text_items.append((backend_name, (max(w - 155, 10), 70), 0.36, (115, 130, 155), 1))

    # 3. Alert banners
    banner_y = panel_h + 10
    if analysis.calibration.active:
        pct = int(analysis.calibration.progress * 100)
        _blend_rect(frame, 14, banner_y, w - 14, banner_y + 32, (180, 125, 45), 0.85)
        text_items.append((canvas_tr.t("calibrating_banner", pct=pct), (24, banner_y + 22), 0.50, (255, 255, 255), 1))
    elif analysis.is_drowsy:
        _blend_rect(frame, 14, banner_y, w - 14, banner_y + 32, (45, 50, 215), 0.88)
        text_items.append((canvas_tr.t("drowsy_banner", sec=analysis.closure_duration_ms / 1000.0), (24, banner_y + 22), 0.52, (255, 255, 255), 1))
    elif wellness.break_status.in_break:
        rem = int(wellness.break_status.break_seconds_remaining)
        _blend_rect(frame, 14, banner_y, w - 14, banner_y + 32, (145, 130, 35), 0.86)
        text_items.append((canvas_tr.t("break_banner", sec=rem), (24, banner_y + 22), 0.50, (255, 255, 255), 1))
    elif wellness.dry_eye_warning:
        _blend_rect(frame, 14, banner_y, w - 14, banner_y + 32, (35, 125, 210), 0.86)
        text_items.append((canvas_tr.t("dry_eye_banner", bpm=wellness.current_bpm), (24, banner_y + 22), 0.48, (255, 255, 255), 1))

    # 4. Real-time EAR waveform graph (bottom-right)
    if show_graph and len(ear_history) >= 2 and w >= 420 and h >= 240:
        gw, gh = min(240, w // 3), 88
        gx, gy = w - gw - 14, h - gh - 38
        _blend_rect(frame, gx, gy, gx + gw, gy + gh, (18, 22, 32), 0.78)
        cv2.rectangle(frame, (gx, gy), (gx + gw, gy + gh), (65, 78, 102), 1)

        ear_min, ear_max = 0.08, 0.42

        def _to_y(val: float) -> int:
            norm = max(0.0, min(1.0, (val - ear_min) / (ear_max - ear_min)))
            return int(gy + gh - 8 - norm * (gh - 20))

        ty = _to_y(analysis.threshold)
        cv2.line(frame, (gx + 4, ty), (gx + gw - 4, ty), (70, 175, 255), 1, cv2.LINE_AA)

        recent = list(ear_history)[-100:]
        n = len(recent)
        pts = [
            (int(gx + 6 + (idx / max(1, n - 1)) * (gw - 12)), _to_y(ear_val))
            for idx, (_, ear_val) in enumerate(recent)
        ]
        if len(pts) >= 2:
            cv2.polylines(
                frame,
                [np.array(pts, dtype=np.int32)],
                isClosed=False,
                color=(110, 235, 175),
                thickness=2,
                lineType=cv2.LINE_AA,
            )

        text_items.append((canvas_tr.t("ear_waveform"), (gx + 8, gy + 15), 0.38, (175, 190, 210), 1))

    # 5. Bottom hotkey bar
    _blend_rect(frame, 0, h - 28, w, h, (18, 22, 32), 0.78)
    text_items.append((canvas_tr.t("hotkeys"), (12, h - 9), 0.40, (175, 190, 210), 1))

    _draw_text_batch(frame, text_items, use_unicode=(canvas_tr.lang != "en" and unicode_ready))
    return frame
