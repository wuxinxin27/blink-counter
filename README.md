# 👁️ Blink Counter

[![Live Web App](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-0ea5e9?logo=githubpages&logoColor=white)](https://wuxinxin27.github.io/blink-counter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/OS-macOS%20%7C%20Linux%20%7C%20Windows-2ea44f)](#quick-start)

A **cross-platform automatic eye blink counter & eye-wellness tracker** that uses your computer's webcam to count blinks in real time, monitor blink health, prevent dry eyes and fatigue, and export detailed session analytics.

Includes **two ways to run** in one repository:
1. **Native Python Desktop & CLI App** (`blink_counter/`) — powered by OpenCV & MediaPipe (with an automatic OpenCV Haar fallback), supporting live HUD, real-time EAR waveform, headless background tracking, video-file analysis, and automatic CSV/JSON logging.
2. **Zero-Install Browser Web App** (`web/`) — powered by MediaPipe Face Landmarker in WebAssembly. Runs 100% locally in Chrome, Edge, Safari, or Firefox on macOS, Linux, and Windows (and auto-deploys to GitHub Pages).

---

## ✨ Features

- **Automatic Real-Time Blink Counting**: Computes the **Eye Aspect Ratio (EAR)** from 6 eye landmarks per eye with EMA smoothing, hysteresis, duration bounds, and cooldown filtering to avoid double counts.
- **3-Second Auto-Calibration**: Automatically learns your personal open-eye baseline EAR and adapts the blink threshold (great for different eye shapes, glasses, and lighting).
- **Live Blink Rate (BPM) & Dry-Eye Alerts**: Tracks rolling 60-second blinks-per-minute (healthy range: 15–20 BPM) and gently alerts you if your blink rate drops too low while staring at a screen.
- **Drowsiness / Prolonged Closure Detection & PERCLOS**: Distinguishes natural blinks from extended eye closure (> 1.5 s) and computes rolling **PERCLOS** (% of time eyes are closed).
- **20-20-20 Eye Break Timer**: Built-in reminder every 20 minutes to look 20 feet (6 m) away for 20 seconds.
- **Live HUD + Real-Time EAR Waveform**: Draws eye landmark contours, a live EAR sparkline chart with threshold line, and status banners.
- **Headless / Background Mode & Video Analysis**: Run without a GUI window (`--headless`) or analyze recorded videos (`--source clip.mp4`).
- **Session Logging & Export**: Exports every blink event to **CSV** and full session statistics to **JSON**.
- **Privacy-First**: All camera frames are processed **100% locally** on your machine. No images or video are ever uploaded.

---

## 🚀 Quick Start

### Option A: Zero-Install Browser Web App (Works on macOS, Linux & Windows)

Launch locally with standard Python 3 (no `pip install` needed):

```bash
git clone https://github.com/wuxinxin27/blink-counter.git
cd blink-counter
python3 -m blink_counter --web
```

*(On Windows, use `python -m blink_counter --web`.)*

Or open the hosted GitHub Pages web app (once GitHub Pages is enabled in repository settings):
`https://wuxinxin27.github.io/blink-counter/`

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

*(Optional: install as an editable CLI command with `pip install -e .` so you can run `blink-counter` directly.)*

#### 2. Run the app

```bash
python -m blink_counter
```

---

## ⌨️ Interactive Hotkeys (Desktop HUD)

| Key | Action |
| --- | --- |
| `Q` / `ESC` | Quit and save session logs |
| `R` | Reset blink count and session timer |
| `C` | Re-run 3-second open-eye auto-calibration |
| `P` | Pause / Resume tracking |
| `M` | Mute / Unmute audio alerts |
| `G` | Toggle real-time EAR waveform graph |
| `O` | Toggle eye landmark contour overlay |
| `S` | Save a CSV + JSON session snapshot immediately |

---

## 🛠️ CLI Options

```text
python -m blink_counter [options]

  --web                  Launch the Browser Web App locally (zero extra dependencies)
  --camera INDEX         Webcam index (default: 0)
  --source PATH          Analyze a video file instead of a live webcam
  --threshold FLOAT      Fixed EAR threshold (disables auto-calibration, e.g. 0.21)
  --no-calibrate         Skip initial 3-second auto-calibration
  --backend MODE         Vision backend: auto | mediapipe | haar (default: auto)
  --headless             Run without opening a video window (prints live stats to terminal)
  --low-bpm FLOAT        Dry-eye alert threshold in BPM (default: 10.0)
  --drowsy-seconds SEC   Continuous closure duration for drowsiness alert (default: 1.5)
  --break-minutes MIN    20-20-20 eye break interval in minutes; 0 disables (default: 20)
  --no-sound             Mute audible alerts
  --no-log               Disable saving session CSV/JSON logs on exit
  --log-dir PATH         Custom directory for session logs
```

### Examples

```bash
# Run quietly in the background while working (terminal stats + CSV/JSON logs)
python -m blink_counter --headless

# Analyze a pre-recorded video with a custom EAR threshold
python -m blink_counter --source demo.mp4 --threshold 0.22

# Use the lightweight OpenCV Haar fallback backend
python -m blink_counter --backend haar
```

---

## 💻 OS-Specific Camera Notes

- **macOS**: Uses `AVFoundation` automatically. On first run, grant camera permission to your Terminal or IDE under **System Settings → Privacy & Security → Camera**.
- **Windows**: Uses `DirectShow` (`CAP_DSHOW`) with automatic fallback. Ensure camera access is enabled under **Settings → Privacy & security → Camera**.
- **Linux**: Uses `V4L2` (`CAP_V4L2`) with automatic fallback. Ensure your user has access to `/dev/video*` (`sudo usermod -aG video $USER`).

---

## 📐 How Blink Detection Works

For each eye, 6 facial landmarks $p_1 \dots p_6$ are extracted from MediaPipe Face Landmarker (`[33, 160, 158, 133, 153, 144]` for the left eye and `[362, 385, 387, 263, 373, 380]` for the right eye) and combined using the **Eye Aspect Ratio (EAR)** formula (Soukupová & Čech, 2016):

$$\text{EAR} = \frac{\|p_2 - p_6\| + \|p_3 - p_5\|}{2 \|p_1 - p_4\|}$$

When eyes are open, EAR stays roughly constant (~0.25–0.35). During a blink, EAR drops sharply below the adaptive threshold and returns above `threshold + hysteresis` within 50–800 ms.

---

## 🧪 Running Tests

The core detection, eye-wellness analytics, session logger, CLI parser, and web server are covered by unit tests that run on macOS, Linux, and Windows without requiring a webcam:

```bash
python -m unittest discover -s tests -v
```

---

## 📁 Project Structure

```text
blink-counter/
├── blink_counter/
│   ├── cli.py          # CLI argument parser and desktop/headless/web runtime
│   ├── config.py       # Dataclass configurations & OS-specific cache/log paths
│   ├── detector.py     # EAR math, blink state machine, auto-calibration, PERCLOS
│   ├── hud.py          # OpenCV live HUD & real-time EAR waveform graph
│   ├── logger.py       # Session CSV & JSON exporter
│   ├── vision.py       # Cross-platform camera capture & MediaPipe/Haar extractors
│   ├── web_server.py   # Zero-dependency local HTTP server for `--web` mode
│   └── wellness.py     # Rolling BPM, dry-eye alerts, 20-20-20 timer & audio alerts
├── web/
│   ├── index.html      # Zero-install Browser Web App UI
│   ├── styles.css      # Responsive dark theme
│   └── app.js          # Client-side MediaPipe FaceLandmarker + EAR chart + export
├── tests/              # Cross-platform unit tests
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
