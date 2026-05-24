# Bird Tracker

A macOS app that tracks birds in the sky using your iPhone camera. Point the iPhone at the sky, launch the app, and watch birds get detected and traced in real time — in your browser.

## How it works

The app uses background subtraction (OpenCV MOG2) to detect anything moving in the sky. Each moving blob gets a persistent ID and a colour trail showing its recent flight path. No machine learning, no cloud — runs entirely on your Mac.

## Setup

**Requirements:** macOS, [uv](https://docs.astral.sh/uv/)

Install uv if you don't have it:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install dependencies (once):
```bash
uv pip install -r requirements.txt
```

## Launch

Double-click **`start.command`** in Finder. The browser opens automatically.

Or from the terminal:
```bash
uv run python3 main.py
```

## iPhone camera

Enable **Continuity Camera** (iPhone and Mac on the same Apple ID, Bluetooth on). The iPhone appears as a camera device. On a MacBook with a built-in FaceTime camera, the iPhone is usually device index 1 — set it in `.env`:

```env
CAMERA_INDEX=1
```

## Tuning

Open the sidebar in the browser. Key controls:

| Slider | What it does |
|--------|-------------|
| Motion threshold | MOG2 sensitivity — lower catches subtler movement, higher ignores wind/leaves |
| Min / Max blob size | Filter by pixel area — use "Blobs this frame" readout to calibrate |
| Min track age | Frames a blob must persist before it's shown — raise to suppress rain/flickers |

Watch **Blobs this frame** while adjusting to see what the tracker currently detects.
