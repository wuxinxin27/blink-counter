# 👁️ Blink Counter

[![Download Latest Release](https://img.shields.io/github/v/release/wuxinxin27/blink-counter?label=Download&color=10b981&logo=github)](https://github.com/wuxinxin27/blink-counter/releases/latest)
[![Live Web / PWA](https://img.shields.io/badge/Try%20Online-Web%20%2F%20PWA-0ea5e9?logo=googlechrome&logoColor=white)](https://wuxinxin27.github.io/blink-counter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/OS-macOS%20%7C%20Windows%20%7C%20Linux-2ea44f)](#download--install)

**Protect your eyes effortlessly while working at your computer.**

Blink Counter is a lightweight (~10–15 MB), **100% free & on-device** desktop app that tracks your blink frequency in real time, gently alerts you with unmissable pop-ups & chimes when your blink rate drops too low, and guides you through **20-20-20 far-gaze eye breaks** — all without ever uploading a single video frame.

---

## 🚀 Download & Install *(No Python or Coding Needed)*

### Option 1: Lightweight Native Desktop App (Tauri — ~10–15 MB, Offline)

Download the installer for your OS from [**GitHub Releases**](https://github.com/wuxinxin27/blink-counter/releases/latest):

| Operating System | Installer | Highlights |
| --- | --- | --- |
| **macOS (Apple Silicon M1–M4)** | `Blink Counter_*_aarch64.dmg` | Drag to Applications · Menu bar tray residency |
| **macOS (Intel)** | `Blink Counter_*_x64.dmg` | Drag to Applications · Menu bar tray residency |
| **Windows (64-bit)** | `Blink Counter_*_x64-setup.exe` / `.msi` | Standard installer · System tray residency |
| **Linux (64-bit)** | `Blink Counter_*_amd64.AppImage` / `.deb` | Portable AppImage or Debian/Ubuntu package |

> **100% Offline & Private**: The AI vision model (`face_landmarker.task`) and WebAssembly runtime are bundled right inside the installer. Zero cloud APIs, zero accounts, \$0 forever.

### Option 2: Instant Browser / PWA Install *(Zero Download)*

1. Open **https://wuxinxin27.github.io/blink-counter/** in Chrome or Edge.
2. Click **`⬇ Install App` / `⬇ 安装到本地`** in the top bar to install it as a standalone desktop window.

---

## ✨ Key Features

- **Blink-Frequency-First Experience**: Clear real-time **Blink Rate (blinks/min)**, **Total Blinks**, **Average Rate**, and a **Blink Frequency Trend Chart** with a shaded healthy zone (15–20 BPM) and automatic background calibration.
- **Unmissable Pop-Up Alerts & Multi-Note Chimes**:
  - **Dry-Eye Reminder**: Alerts you when your blink rate stays below your threshold (default: 10 BPM).
  - **20-20-20 Far-Gaze Break**: Reminds you every 20 minutes to look 20 ft (6 m) away for 20 seconds with a live countdown & completion chime.
  - **Drowsiness Alert**: Warns you on prolonged eye closure.
  - **Always-On-Top Desktop Surfacing**: In the native Tauri app, alerts surface cleanly above other apps + send native OS notifications even when tucked in the system tray.
- **System Tray / Menu Bar Residency**: Closing the window hides Blink Counter to your menu bar / system tray so it quietly protects your eyes without cluttering your screen.
- **Ultra-Low Battery Eco Mode**:
  - **15 FPS inference cap** + **1.5 FPS no-face idle backoff** when you step away.
  - **Zero-Video-Render Mode**: Automatically stops all video, canvas, chart, and DOM rendering when minimized/hidden to tray, plus a manual **Hide Video Preview** toggle.
  - **Duty-Cycle Sampling**: Optional 60s ON / 240s camera-completely-OFF cycling for all-day battery life.
- **Multi-Language UI (Auto-Detected)**: Switch live between **English**, **简体中文**, **日本語**, and **Español**.
- **Session Analytics Export**: Export your blink history to **CSV** or **JSON** in one click.

---

## 🛠️ Automated Cross-Platform Releases (GitHub Actions)

Every version tag push (`git tag v2.0.0 && git push origin v2.0.0`) or manual run of **Actions → Build & Release Cross-Platform Desktop App (Tauri)** automatically:
1. Bundles offline MediaPipe WASM + `face_landmarker.task` via `desktop/scripts/fetch_vendor.py`.
2. Builds signed/packaged installers in parallel for **macOS (Apple Silicon + Intel)**, **Windows x64**, and **Linux x64**.
3. Publishes all installers to **GitHub Releases**.

---

## 💻 For Developers (Local Development & Python CLI)

### Tauri Desktop App (Rust + Node.js)
```bash
cd desktop
npm install
python3 scripts/fetch_vendor.py
npm run dev      # Run desktop app in development mode
npm run build    # Build native installer for your current OS
```

### Python CLI & Headless / Video-File Analyzer
```bash
# Launch local web UI with zero pip dependencies
python3 -m blink_counter --web

# Run Python desktop/headless analyzer
pip install -r requirements.txt
python3 -m blink_counter --eco --headless
python3 -m blink_counter --source clip.mp4

# Run cross-platform unit tests
python3 -m unittest discover -s tests -v
```

---

## 📁 Project Structure

```text
blink-counter/
├── desktop/                     # Tauri v2 lightweight native desktop shell (Rust)
│   ├── package.json
│   ├── scripts/fetch_vendor.py  # Bundles offline MediaPipe WASM & AI model at build time
│   └── src-tauri/
│       ├── Cargo.toml
│       ├── tauri.conf.json
│       ├── Info.plist           # macOS camera privacy permission description
│       ├── capabilities/        # Tauri v2 permission scopes
│       ├── icons/               # Multi-platform .icns / .ico / .png app icons
│       └── src/lib.rs           # System tray, always-on-top alerts, native notifications
├── web/                         # Shared commercial UI (used by Tauri Desktop + GitHub Pages PWA)
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── manifest.json & sw.js    # PWA support
│   └── icons/
├── blink_counter/               # Python CLI, headless analyzer & pure-Python core engine
├── tests/                       # Cross-platform Python unit tests
├── packaging/                   # Icon generator & optional Python PyInstaller builder
└── .github/workflows/
    ├── ci.yml                   # Cross-platform Python CI (Ubuntu / macOS / Windows)
    └── release-desktop.yml      # Automated 4-target Tauri build & GitHub Release workflow
```

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
