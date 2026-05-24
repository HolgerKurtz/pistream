# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Branches

- **`main`** — original YOLO11 pose/detect system with music generation (human tracking)
- **`bird-tracking`** — this branch; pure-CV bird detection and trail drawing, no YOLO

## Running

```bash
# Terminal 1 — mock video stream (webcam or file)
uv run python3 mock_stream.py

# Terminal 2 — bird tracker + web UI
uv run python3 main.py
```

Open `http://localhost:5001` in a browser. On Raspberry Pi run `pi_stream.py` instead of `mock_stream.py`.

**Install dependencies:**
```bash
uv pip install -r requirements.txt
```

Pi dependencies (`requirements-pi.txt`): only `pyzmq`, `numpy`, `python-dotenv`. `picamera2` is pre-installed on Raspberry Pi OS.

## Configuration (`.env`)

```env
PORT=5555             # ZMQ port shared by streamer and server
PI_IP=localhost       # IP of the Pi (or localhost for mock)
MOCK_SOURCE=0         # 0 = webcam, path = video file, "noise" = random frames
WEB_PORT=5001         # Flask web UI port (avoid 5000 — macOS uses it for AirPlay)

STREAM_WIDTH=1280     # capture + ZMQ frame width
STREAM_HEIGHT=720     # capture + ZMQ frame height
STREAM_QUALITY=85     # JPEG quality sent over ZMQ (1–100)
DISPLAY_QUALITY=85    # JPEG quality re-encoded for browser MJPEG

BG_HISTORY=500        # MOG2 frame history for background model
BG_VAR_THRESHOLD=16   # MOG2 sensitivity — lower = more sensitive
BIRD_MIN_AREA=60      # min contour area in px (scaled for 1280×720)
BIRD_MAX_AREA=6000    # max contour area in px (scaled for 1280×720)
TRAIL_LENGTH=60       # past positions drawn per bird
MAX_DISAPPEARED=10    # frames before a lost track is removed
WARMUP_FRAMES=60      # frames to run fast background learning at startup
MIN_TRACK_AGE=4       # frames a blob must persist before it's shown as a bird
```

## Architecture

```
mock_stream.py / pi_stream.py
        │ ZMQ PUB  (JPEG frames over TCP)
        ▼
    main.py          ← entry point, wires everything together
    ├── zmq_loop.py  ← receives frames, runs BirdTracker, pushes results to AppState
    ├── state.py     ← thread-safe AppState shared between ZMQ loop and Flask
    ├── web_app.py   ← Flask: MJPEG /video_feed, SSE /stats, POST /control
    ├── bird_tracker.py  ← background subtraction + centroid tracker
    └── config.py    ← all env-var loading
```

**Thread model:** `zmq_loop.run()` runs in a daemon thread; Flask runs in the main thread. `AppState` is the only shared object — all access goes through its methods which acquire an internal lock.

**`BirdTracker` pipeline per frame:**
1. BGR → greyscale
2. MOG2 background subtraction (fast learning rate during `warmup_frames`)
3. Morphological open + dilate to clean the mask
4. Contour filter by area (`BIRD_MIN_AREA` … `BIRD_MAX_AREA`)
5. Centroid-matching tracker — assigns persistent IDs, keeps a trail deque per bird
6. Only tracks with age ≥ `MIN_TRACK_AGE` are shown (suppresses startup noise and tree bursts)
7. Annotated greyscale-to-BGR frame with fading coloured trails

## Future: p5.js Visualisation (Step 2)

Plan: add a WebSocket broadcast of `AppState.get_stats()` track positions each frame. A p5.js client connects and draws flight paths with creative stroke styles. The ZMQ/camera layer stays unchanged.
