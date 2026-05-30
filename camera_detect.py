import cv2
import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def _get_camera_names() -> list:
    """Return camera display names from macOS system_profiler, in AVFoundation order."""
    try:
        r = subprocess.run(
            ['system_profiler', 'SPCameraDataType', '-json'],
            capture_output=True, text=True, timeout=5,
        )
        data = json.loads(r.stdout)
        return [c['_name'] for c in data.get('SPCameraDataType', [])]
    except Exception:
        return []


def detect() -> list:
    """
    Probe camera indices 0-4 and return a list of dicts:
      {'index': int, 'label': str}
    Uses system_profiler to get real camera names where available.
    """
    found_indices = []
    found_sizes = []

    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    saved_stderr = os.dup(2)
    os.dup2(devnull_fd, 2)
    try:
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                found_indices.append(i)
                found_sizes.append((w, h))
                cap.release()
    finally:
        os.dup2(saved_stderr, 2)
        os.close(saved_stderr)
        os.close(devnull_fd)

    names = _get_camera_names()
    cameras = []
    for pos, (i, (w, h)) in enumerate(zip(found_indices, found_sizes)):
        name = names[pos] if pos < len(names) else f'Camera {i}'
        cameras.append({'index': i, 'label': f'{name}  ({w}×{h})'})

    logger.info(f"Cameras detected: {[c['label'] for c in cameras]}")
    return cameras
