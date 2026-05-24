import cv2
import zmq
import numpy as np
import time
import logging
import threading
from typing import Optional, Tuple

from bird_tracker import BirdTracker
from state import AppState

logger = logging.getLogger(__name__)

_RECV_TIMEOUT_MS = 500  # recv blocks for at most this long, then checks stop_event


def initialize(host: str, port: int) -> Tuple[zmq.Context, zmq.Socket]:
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.RCVTIMEO, _RECV_TIMEOUT_MS)
    socket.connect(f"tcp://{host}:{port}")
    socket.setsockopt_string(zmq.SUBSCRIBE, '')
    logger.info(f"ZMQ connected to tcp://{host}:{port}")
    return context, socket


def _receive_frame(socket: zmq.Socket) -> Optional[np.ndarray]:
    try:
        buf = socket.recv()
        arr = np.frombuffer(buf, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except zmq.Again:
        return None  # timeout — normal, just means no frame arrived yet
    except zmq.ZMQError as e:
        logger.error(f"ZMQ receive error: {e}")
        return None
    except Exception as e:
        logger.error(f"Frame decode error: {e}")
        return None


def run(
    socket: zmq.Socket,
    tracker: BirdTracker,
    state: AppState,
    stop_event: threading.Event,
    display_quality: int = 85,
) -> None:
    frame_count = 0
    last_fps_time = time.time()
    current_fps = 0.0
    prev_tracking = True

    while not stop_event.is_set():
        frame = _receive_frame(socket)
        if frame is None:
            continue  # timeout or error — loop and check stop_event

        params = state.get_tracker_params()
        if params['flip_horizontal']:
            frame = cv2.flip(frame, 1)

        # Reset all tracks when the user pauses tracking
        if prev_tracking and not params['tracking_active']:
            tracker.reset()
        prev_tracking = params['tracking_active']

        if params['tracking_active']:
            tracker.min_area = params['min_area']
            tracker.max_area = params['max_area']
            tracker.min_track_age = params['min_track_age']
            tracker.bg_subtractor.setVarThreshold(params['bg_var_threshold'])

            results, annotated = tracker.process_frame(frame)
            active = len(results.tracks)
            warming_up = results.warming_up
            areas = results.detection_areas
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            annotated = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            active = 0
            warming_up = False
            areas = []

        _, jpeg = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), display_quality])

        frame_count += 1
        now = time.time()
        elapsed = now - last_fps_time
        if elapsed >= 1.0:
            current_fps = round(frame_count / elapsed, 1)
            frame_count = 0
            last_fps_time = now

        state.push_frame(jpeg.tobytes(), active, current_fps, warming_up, areas)

    logger.info("ZMQ loop stopped.")
