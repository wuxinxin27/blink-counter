"""Generate high-resolution Blink Counter app icons (.png, .ico, and macOS .icns)."""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parent.parent
WEB_ICONS = ROOT / "web" / "icons"
PKG_ASSETS = ROOT / "packaging" / "assets"


def _draw_icon(size: int = 1024):
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded dark navy background card with subtle gradient-like border
    pad = int(size * 0.04)
    radius = int(size * 0.22)
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        fill=(14, 22, 42, 255),
        outline=(56, 189, 248, 170),
        width=max(2, int(size * 0.018)),
    )

    # Inner soft radial glow behind the eye
    cx, cy = size / 2.0, size / 2.0
    for step in range(5, 0, -1):
        r = size * (0.14 + step * 0.045)
        alpha = int(28 - step * 4)
        draw.ellipse(
            [cx - r, cy - r * 0.72, cx + r, cy + r * 0.72],
            fill=(52, 211, 153, max(4, alpha)),
        )

    # Almond eye contour polygon
    eye_w = size * 0.36
    eye_h = size * 0.20
    top_pts = []
    bot_pts = []
    steps = 48
    for i in range(steps + 1):
        t = i / steps
        x = cx - eye_w + 2 * eye_w * t
        arch = math.sin(math.pi * t) ** 1.15
        top_pts.append((x, cy - eye_h * arch))
        bot_pts.append((x, cy + eye_h * arch))
    eye_poly = top_pts + list(reversed(bot_pts))
    draw.polygon(eye_poly, fill=(22, 36, 64, 255))
    draw.line(eye_poly + [eye_poly[0]], fill=(52, 211, 153, 255), width=max(3, int(size * 0.032)), joint="curve")

    # Iris ring (cyan) + pupil (deep navy) + specular highlight (white)
    iris_r = size * 0.125
    draw.ellipse(
        [cx - iris_r, cy - iris_r, cx + iris_r, cy + iris_r],
        fill=(14, 165, 233, 255),
        outline=(186, 230, 253, 255),
        width=max(2, int(size * 0.012)),
    )
    pupil_r = size * 0.058
    draw.ellipse(
        [cx - pupil_r, cy - pupil_r, cx + pupil_r, cy + pupil_r],
        fill=(11, 16, 32, 255),
    )
    glint_r = size * 0.026
    gx, gy = cx + iris_r * 0.34, cy - iris_r * 0.34
    draw.ellipse([gx - glint_r, gy - glint_r, gx + glint_r, gy + glint_r], fill=(255, 255, 255, 240))

    return img


def generate_all_icons() -> Tuple[Path, Path, Path]:
    """Generate PNG (web & desktop), ICO (Windows), and ICNS (macOS) icon assets."""
    WEB_ICONS.mkdir(parents=True, exist_ok=True)
    PKG_ASSETS.mkdir(parents=True, exist_ok=True)

    master = _draw_icon(1024)
    png_1024 = PKG_ASSETS / "icon.png"
    master.save(png_1024, format="PNG")

    # PWA icons
    master.resize((192, 192)).save(WEB_ICONS / "icon-192.png", format="PNG")
    master.resize((512, 512)).save(WEB_ICONS / "icon-512.png", format="PNG")

    # Windows multi-size .ico
    ico_path = PKG_ASSETS / "icon.ico"
    master.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    # macOS .icns (written directly by Pillow — works cross-platform without iconutil quirks)
    icns_path = PKG_ASSETS / "icon.icns"
    master.save(icns_path, format="ICNS")
    iconset_dir = PKG_ASSETS / "icon.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)

    print(f"[icons] Generated {png_1024}, {ico_path}, {icns_path}, and PWA icons in {WEB_ICONS}")
    return png_1024, ico_path, icns_path


if __name__ == "__main__":
    generate_all_icons()
