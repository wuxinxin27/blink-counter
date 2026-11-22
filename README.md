# 👁️ Blink Counter

[![Live Web App](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-0ea5e9?logo=githubpages&logoColor=white)](https://wuxinxin27.github.io/blink-counter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/OS-macOS%20%7C%20Linux%20%7C%20Windows-2ea44f)](#quick-start)

A **cross-platform automatic eye blink counter & eye-wellness tracker** that uses your computer's webcam to count blinks in real time, monitor blink health, prevent dry eyes and fatigue, save laptop battery with **Eco Power-Saving Mode**, and switch languages seamlessly (**English / 简体中文 / 日本語 / Español**).

Includes **two ways to run** in one repository:
1. **Native Python Desktop & CLI App** (`blink_counter/`) — powered by OpenCV & MediaPipe (`RunningMode.VIDEO` tracking + OpenCV Haar fallback), supporting a clean blink-frequency HUD, live BPM trend chart, headless background tracking, Eco power-saving & duty-cycle modes, video-file analysis, and automatic CSV/JSON logging.
2. **Zero-Install Browser Web App** (`web/`) — powered by MediaPipe Face Landmarker in WebAssembly. Runs 100% locally in Chrome, Edge, Safari, or Firefox on macOS, Linux, and Windows, and is hosted live on GitHub Pages.

---

## ✨ Features

- **Blink-Frequency-First Interface**: Focuses directly on what matters to users — **Live Blink Rate (BPM)**, **Total Blinks**, **Average Rate**, and a **Blink Frequency Trend Chart** with a shaded healthy zone (15–20 BPM) and automatic calibration under the hood.
- **⚡ Eco Power-Saving Mode & Duty-Cycle Sampling**:
  - Caps inference to **15 FPS** (a 150–300 ms blink still spans 2–5 frames reliably).
  - Downscales capture & inference frames (`480×270` / `280px` width) and uses `RunningMode.VIDEO` temporal tracking.
  - **No-Face Idle Backoff**: Automatically drops polling to **1.5 FPS** after 5 seconds when you step away.
  - **ROI-only HUD blending**: Eliminates full-frame copies when drawing overlays.
  - **Duty-Cycle Wellness Sampling (`--duty-cycle 60:240`)**: Monitors for 60 s, then **completely releases the camera hardware** for 240 s to save laptop battery.
- **🌐 Multi-Language Support (i18n)**: Switch live between **English (`en`)**, **简体中文 (`zh`)**, **日本語 (`ja`)**, and **Español (`es`)** via `--lang`, the `L` hotkey on desktop, or the top-bar dropdown in the Web App (auto-detects your OS/browser language by default).
- **3-Second Auto-Calibration**: Automatically learns your personal open-eye baseline EAR and adapts the blink threshold.
- **Live Blink Rate (BPM) & Dry-Eye Alerts**: Tracks rolling 60-second blinks-per-minute (healthy range: 15–20 BPM) and gently alerts you if your blink rate drops too low.
- **Drowsiness / Prolonged Closure Detection & PERCLOS**: Distinguishes natural blinks from extended eye closure (> 1.5 s) and computes rolling **PERCLOS**.
- **20-20-20 Eye Break Timer**: Built-in reminder every 20 minutes to look 20 feet (6 m) away for 20 seconds.
- **Session Logging & Export**: Exports every blink event to **CSV** and full session statistics to **JSON**.
- **Privacy-First**: All camera frames are processed **100% locally** on your machine. No images or video are ever uploaded.

---

## 🚀 Quick Start

### Option A: Zero-Install Browser Web App (macOS, Linux & Windows)

Try it immediately online:
👉 **https://wuxinxin27.github.io/blink-counter/**

Or run locally with standard Python 3 (no `pip install` needed):

```bash
git clone https://github.com/wuxinxin27/blink-counter.git
cd blink-counter
python3 -m blink_counter --web
# Open directly in Chinese / Japanese / Spanish:
python3 -m blink_counter --web --lang zh
```

*(On Windows, use `python -m blink_counter --web`.)*

---

### Option B: Native Python Desktop App

#### 1. Clone & create a virtual environment

**macOS / Linux:**
```bash
git clone https://github.com/wuxinxin27/blink-counter.git
cd blink-counter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/wuxinxin27/blink-counter.git
cd blink-counter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### 2. Run the app

```bash
# Standard desktop HUD
python -m blink_counter

# Battery-friendly Eco mode (15 FPS, low-res, idle backoff)
python -m blink_counter --eco

# Run in Simplified Chinese with Eco mode
python -m blink_counter --eco --lang zh

# Ultra-low-power headless wellness sampling (60s on, 240s camera completely off)
python -m blink_counter --eco --headless --duty-cycle 60:240
```

---

## ⌨️ Interactive Hotkeys (Desktop HUD)

| Key | Action |
| --- | --- |
| `Q` / `ESC` | Quit and save session logs |
| `R` | Reset blink count and session timer |
| `C` | Re-run 3-second open-eye auto-calibration |
| `P` | Pause / Resume tracking |
| `E` | Toggle **Eco low-power mode** (15 FPS cap) |
| `L` | Cycle UI language (**English → 简体中文 → 日本語 → Español**) |
| `M` | Mute / Unmute audio alerts |
| `G` | Toggle real-time EAR waveform graph |
| `O` | Toggle eye landmark contour overlay |
| `S` | Save a CSV + JSON session snapshot immediately |

---

## 🛠️ CLI Options

```text
python -m blink_counter [options]

  --lang LANG            Interface language: auto | en | zh | ja | es (default: auto)
  --web                  Launch the Browser Web App locally (zero extra dependencies)
  --eco                  Enable Eco low-power mode (15 FPS, 480x270, idle backoff)
  --fps FLOAT            Maximum processing FPS (default: 24, eco: 15)
  --idle-fps FLOAT       Reduced FPS when no face is detected (default: 1.5)
  --idle-after SEC       Seconds without a face before idle backoff (default: 5.0)
  --duty-cycle ON:OFF    Periodic sampling in seconds (e.g. 60:240 releases camera for 240s)
  --camera INDEX         Webcam index (default: 0)
  --source PATH          Analyze a video file instead of a live webcam
  --threshold FLOAT      Fixed EAR threshold (disables auto-calibration, e.g. 0.21)
  --no-calibrate         Skip initial 3-second auto-calibration
  --backend MODE         Vision backend: auto | mediapipe | haar (default: auto)
  --headless             Run without opening a video window (lowest UI power)
  --low-bpm FLOAT        Dry-eye alert threshold in BPM (default: 10.0)
  --drowsy-seconds SEC   Continuous closure duration for drowsiness alert (default: 1.5)
  --break-minutes MIN    20-20-20 eye break interval in minutes; 0 disables (default: 20)
  --no-sound             Mute audible alerts
  --no-log               Disable saving session CSV/JSON logs on exit
  --log-dir PATH         Custom directory for session logs
```

---

## 💻 OS-Specific Camera Notes

- **macOS**: Uses `AVFoundation` automatically. On first run, grant camera permission to your Terminal or IDE under **System Settings → Privacy & Security → Camera**.
- **Windows**: Uses `DirectShow` (`CAP_DSHOW`) with automatic fallback. Enable camera access under **Settings → Privacy & security → Camera**.
- **Linux**: Uses `V4L2` (`CAP_V4L2`) with automatic fallback. Ensure your user has access to `/dev/video*` (`sudo usermod -aG video $USER`).

---

## 🧪 Running Tests

```bash
python -m unittest discover -s tests -v
```

---

## 📁 Project Structure

```text
blink-counter/
├── blink_counter/
│   ├── cli.py          # CLI argument parser and power-aware runtime loop
│   ├── config.py       # Dataclass configurations & OS-specific cache/log paths
│   ├── detector.py     # EAR math, blink state machine, auto-calibration, PERCLOS
│   ├── hud.py          # ROI-blended OpenCV HUD with Unicode/CJK font support
│   ├── i18n.py         # Multi-language translations (en, zh, ja, es) & auto-detect
│   ├── logger.py       # Session CSV & JSON exporter
│   ├── power.py        # Eco FPS pacing, no-face idle backoff & duty-cycle controller
│   ├── vision.py       # Cross-platform camera capture & MediaPipe VIDEO/Haar extractors
│   ├── web_server.py   # Zero-dependency local HTTP server for `--web` mode
│   └── wellness.py     # Rolling BPM, dry-eye alerts, 20-20-20 timer & audio alerts
├── web/
│   ├── index.html      # Zero-install Browser Web App UI (with language switcher & Eco mode)
│   ├── styles.css      # Responsive dark theme
│   └── app.js          # Client-side MediaPipe FaceLandmarker + Eco mode + i18n + export
├── tests/              # Cross-platform unit tests
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
