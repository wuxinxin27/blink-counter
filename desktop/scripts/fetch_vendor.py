"""Download offline MediaPipe Tasks Vision WASM + FaceLandmarker model into `web/vendor/` for Tauri bundles."""

from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
VENDOR_DIR = ROOT / "web" / "vendor"

FILES = {
    "mediapipe/vision_bundle.mjs": "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs",
    "mediapipe/wasm/vision_wasm_internal.js": "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm/vision_wasm_internal.js",
    "mediapipe/wasm/vision_wasm_internal.wasm": "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm/vision_wasm_internal.wasm",
    "mediapipe/wasm/vision_wasm_nosimd_internal.js": "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm/vision_wasm_nosimd_internal.js",
    "mediapipe/wasm/vision_wasm_nosimd_internal.wasm": "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm/vision_wasm_nosimd_internal.wasm",
    "models/face_landmarker.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
}


def main() -> int:
    for rel_path, url in FILES.items():
        dest = VENDOR_DIR / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 1024:
            print(f"[vendor] Cached: {rel_path}")
            continue
        print(f"[vendor] Downloading {url} -> {rel_path}")
        urllib.request.urlretrieve(url, dest)
    print("[vendor] Offline MediaPipe assets ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
