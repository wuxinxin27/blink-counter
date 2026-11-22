"""Cross-platform standalone application packager (macOS .app/.dmg, Windows .exe, Linux binary).

Usage:
    python packaging/build_app.py
"""

from __future__ import annotations

import os
import platform
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
APP_NAME = "Blink Counter"
BUNDLE_ID = "io.github.wuxinxin27.blinkcounter"


def _run(cmd: list[str]) -> None:
    print("[build]", " ".join(cmd))
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def _patch_macos_info_plist(app_path: Path, version: str) -> None:
    plist_path = app_path / "Contents" / "Info.plist"
    with plist_path.open("rb") as f:
        plist = plistlib.load(f)

    plist["CFBundleDisplayName"] = APP_NAME
    plist["CFBundleName"] = APP_NAME
    plist["CFBundleIdentifier"] = BUNDLE_ID
    plist["CFBundleShortVersionString"] = version
    plist["CFBundleVersion"] = version
    plist["NSHighResolutionCapable"] = True
    plist["NSCameraUsageDescription"] = (
        "Blink Counter uses your camera locally to measure your blink frequency and protect eye health. "
        "No video ever leaves your computer."
    )
    with plist_path.open("wb") as f:
        plistlib.dump(plist, f)


def _create_macos_dmg(app_path: Path, version: str) -> Path:
    arch = platform.machine().lower()
    dmg_path = DIST_DIR / f"BlinkCounter-{version}-macOS-{arch}.dmg"
    if dmg_path.exists():
        dmg_path.unlink()

    staging_dir = BUILD_DIR / "dmg_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    # Copy .app and add drag-to-Applications symlink
    shutil.copytree(app_path, staging_dir / app_path.name, symlinks=True)
    os.symlink("/Applications", staging_dir / "Applications")

    _run(
        [
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            str(staging_dir),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )
    shutil.rmtree(staging_dir)
    return dmg_path


def main() -> int:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from blink_counter import __version__
    from blink_counter.vision import ensure_face_landmarker_model
    from generate_icons import generate_all_icons

    png_icon, ico_icon, icns_icon = generate_all_icons()

    # Pre-fetch face_landmarker.task into build/models so the packaged app works 100% offline
    bundled_model_dir = BUILD_DIR / "models"
    bundled_model_path = None
    try:
        bundled_model_path = ensure_face_landmarker_model(cache_dir=bundled_model_dir)
    except Exception as exc:
        print(f"[build] Warning: could not pre-bundle face_landmarker.task ({exc}); app will download on first run.")

    sep = ";" if sys.platform == "win32" else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME if sys.platform == "darwin" else "BlinkCounter",
        "--add-data",
        f"{ROOT / 'web'}{sep}web",
        "--collect-data",
        "mediapipe",
        "--collect-binaries",
        "mediapipe",
        "--hidden-import",
        "PIL.Image",
        "--hidden-import",
        "PIL.ImageDraw",
        "--hidden-import",
        "PIL.ImageFont",
    ]
    if bundled_model_path and bundled_model_path.is_file():
        cmd.extend(["--add-data", f"{bundled_model_path}{sep}models"])

    if sys.platform == "darwin":
        cmd.extend(["--onedir", "--osx-bundle-identifier", BUNDLE_ID])
        if icns_icon.is_file():
            cmd.extend(["--icon", str(icns_icon)])
    elif sys.platform == "win32":
        cmd.extend(["--onefile", "--icon", str(ico_icon)])
    else:
        cmd.extend(["--onefile", "--icon", str(png_icon)])

    cmd.append(str(ROOT / "blink_counter" / "app_entry.py"))
    _run(cmd)

    if sys.platform == "darwin":
        app_path = DIST_DIR / f"{APP_NAME}.app"
        _patch_macos_info_plist(app_path, __version__)
        if shutil.which("codesign"):
            _run(["codesign", "--force", "--deep", "--sign", "-", str(app_path)])
        dmg_path = _create_macos_dmg(app_path, __version__)
        print(f"\n[build] macOS app ready:\n  App : {app_path}\n  DMG : {dmg_path}")
    elif sys.platform == "win32":
        exe_path = DIST_DIR / "BlinkCounter.exe"
        print(f"\n[build] Windows executable ready:\n  EXE : {exe_path}")
    else:
        bin_path = DIST_DIR / "BlinkCounter"
        print(f"\n[build] Linux executable ready:\n  BIN : {bin_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
