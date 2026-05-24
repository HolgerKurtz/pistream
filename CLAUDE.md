# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running

Double-click `start.command` in Finder, or from the terminal:

```bash
uv run python3 main.py
```

The browser opens automatically at `http://localhost:5001`.

**First-time setup:**
```bash
uv pip install -r requirements.txt
```

## Configuration (`.env`)

```env
CAMERA_INDEX=0        # 0 = built-in FaceTime, 1 = iPhone (typical on MacBook)
WEB_PORT=5001         # Flask port (avoid 5000 — macOS uses it for AirPlay)
FLIP_HORIZONTAL=false # false = iPhone (natural), true = built-in FaceTime

DISPLAY_QUALITY=85    # JPEG quality for browser MJPEG stream (1–100)

BG_HISTORY=500        # MOG2 frame history for background model
BG_VAR_THRESHOLD=16   # MOG2 sensitivity — lower = more sensitive
BIRD_MIN_AREA=60      # min contour area in px² (scaled for 1280×720)
BIRD_MAX_AREA=6000    # max contour area in px² (scaled for 1280×720)
TRAIL_LENGTH=60       # past positions drawn per bird
MAX_DISAPPEARED=10    # frames before a lost track is removed
WARMUP_FRAMES=60      # frames to run fast background learning at startup
MIN_TRACK_AGE=4       # frames a blob must persist before it's shown as a bird
```

**iPhone camera:** Enable Continuity Camera on the iPhone and Mac (same Apple ID, Bluetooth on). The iPhone appears as a camera device — typically index 1 on a MacBook with a built-in FaceTime camera.

## Architecture

```
main.py              ← entry point; opens camera, wires everything, serves UI
├── camera_loop.py   ← reads frames from cv2.VideoCapture, runs BirdTracker
├── state.py         ← thread-safe AppState shared between camera loop and Flask
├── web_app.py       ← Flask: MJPEG /video_feed, SSE /stats, POST /control
├── bird_tracker.py  ← background subtraction + centroid tracker
└── config.py        ← all env-var loading
```

**Thread model:** `camera_loop.run()` runs in a daemon thread; Flask runs in the main thread. `AppState` is the only shared object — all access goes through its lock-protected methods.

**`BirdTracker` pipeline per frame:**
1. BGR → greyscale
2. MOG2 background subtraction (fast learning rate during `warmup_frames`)
3. Morphological open + dilate to clean the mask
4. Contour filter by area (`BIRD_MIN_AREA` … `BIRD_MAX_AREA`)
5. Centroid-matching tracker — assigns persistent IDs, keeps a trail deque per bird
6. Only tracks with age ≥ `MIN_TRACK_AGE` are shown (suppresses startup noise)
7. Annotated greyscale-to-BGR frame with fading coloured trails

## Future: p5.js Visualisation

Plan: add a WebSocket broadcast of `AppState.get_stats()` track positions each frame. A p5.js client connects and draws flight paths with creative stroke styles. The camera layer stays unchanged.
