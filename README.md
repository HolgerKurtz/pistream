# PISTREAM — Bird Tracker

A lightweight, split-architecture bird tracking system for the Raspberry Pi Zero W.

## Overview

The Pi captures sky footage and streams it over the network. The server detects and tracks birds using background subtraction — no heavy ML model required. A browser-based UI provides a live view and real-time controls.

```
Raspberry Pi Zero W  ──ZMQ (JPEG)──▶  Server
                                          │
                                    BirdTracker
                                   (OpenCV MOG2)
                                          │
                                    Browser UI
                                  (live feed + controls)
```

## Installation

```bash
uv pip install -r requirements.txt
```

Pi dependencies (`requirements-pi.txt`): `pyzmq`, `numpy`, `python-dotenv`. `picamera2` is pre-installed on Raspberry Pi OS.

## Configuration

Create a `.env` file:

```env
PORT=5555
PI_IP=localhost        # IP of the Pi when running on real hardware
MOCK_SOURCE=0          # 0 = webcam, path = video file, "noise" = random frames
WEB_PORT=5001

# Bird tracker tuning (adjustable live in the browser UI)
BG_HISTORY=500
BG_VAR_THRESHOLD=16
BIRD_MIN_AREA=20
BIRD_MAX_AREA=2000
TRAIL_LENGTH=60
MAX_DISAPPEARED=10
WARMUP_FRAMES=60
MIN_TRACK_AGE=4
```

## Usage

### Local development (Mac / Linux)

Open two terminals:

```bash
# Terminal 1 — mock video stream from webcam
uv run python3 mock_stream.py

# Terminal 2 — bird tracker + web UI
uv run python3 main.py
```

Open `http://localhost:5001` in a browser.

### On Raspberry Pi

Transfer `pi_stream.py`, `requirements-pi.txt`, and `.env` to the Pi, then:

```bash
pip install -r requirements-pi.txt
python3 pi_stream.py
```

Set `PI_IP` in `.env` to the Pi's IP address and run `main.py` on the server.

## Tuning

| Parameter | Effect |
|---|---|
| `BG_VAR_THRESHOLD` | Lower = more sensitive. Increase to ignore wind-blown leaves. |
| `BIRD_MIN_AREA` | Raise to filter out insects or noise. |
| `BIRD_MAX_AREA` | Lower to ignore large moving objects (clouds, trees). |
| `MIN_TRACK_AGE` | Frames a blob must persist before it's drawn. Raise to reduce false positives. |
| `WARMUP_FRAMES` | Frames spent learning the initial background. MOG2 won't detect anything during this window. |

All parameters except `WARMUP_FRAMES` can be adjusted live in the browser sidebar without restarting.

## Troubleshooting

**"hundreds of birds" on startup** — increase `WARMUP_FRAMES` or `MIN_TRACK_AGE`.

**Pi Zero: "picam2 module not found"** — run `sudo raspi-config` → Performance Options → GPU Memory → set to 128, then reboot.
