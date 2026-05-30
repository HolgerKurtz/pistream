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
BG_VAR_THRESHOLD=4    # MOG2 sensitivity — kept very low (max sensitivity); brightness filter does the real work
BIRD_MIN_AREA=10      # min contour area in px² — very small to catch any bird size
BIRD_MAX_AREA=50000   # max contour area in px² — very large; brightness filter rejects clouds
BIRD_MAX_BRIGHTNESS=120  # starting value; auto-calibrated from sky on launch, resume, and every interval
SKY_DARKNESS_PCT=25   # live-adjustable in UI: how much darker than sky mean a bird must be (%)
RECALIBRATE_INTERVAL=15  # seconds between automatic sky brightness recalibrations
TRAIL_LENGTH=60       # past positions remembered and drawn per bird
TRAIL_THICKNESS=3     # max trail line width in px at tip; tapers to 1 px at tail
MAX_DISAPPEARED=10    # frames before a lost track is removed
MAX_MATCH_DISTANCE=150  # max px a detection can be from a track's last position to be considered the same bird
WARMUP_FRAMES=60      # frames to run fast background learning at startup
MIN_TRACK_AGE=2       # frames a blob must persist before it's shown as a bird
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
3. Morphological dilate to merge nearby fragments (open step removed — it killed tiny birds at 0.5× scale)
4. Contour filter by area (`BIRD_MIN_AREA` … `BIRD_MAX_AREA`)
5. Centroid-matching tracker — assigns persistent IDs, keeps a trail deque per bird
6. Only tracks with age ≥ `MIN_TRACK_AGE` are shown (suppresses startup noise)
7. Annotated greyscale-to-BGR frame with fading coloured trails

