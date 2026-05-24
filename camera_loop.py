import cv2
import time
import logging
import threading

from bird_tracker import BirdTracker
from state import AppState

logger = logging.getLogger(__name__)


def initialize(camera_index: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera {camera_index}")
    logger.info(f"Camera {camera_index} opened: "
                f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}×"
                f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} "
                f"@ {cap.get(cv2.CAP_PROP_FPS):.0f}fps")
    return cap


def run(
    cap: cv2.VideoCapture,
    tracker: BirdTracker,
    state: AppState,
    stop_event: threading.Event,
    display_quality: int = 85,
) -> None:
    frame_count = 0
    last_fps_time = time.time()
    current_fps = 0.0
    prev_tracking = True

    _TIMING_INTERVAL = 30
    timing_count = 0
    t_capture = t_track = t_encode = 0.0

    while not stop_event.is_set():
        new_idx = state.pop_camera_changed()
        if new_idx is not None:
            logger.info(f"Switching to camera {new_idx}")
            cap.release()
            time.sleep(0.5)  # give AVFoundation time to release the device
            cap = cv2.VideoCapture(new_idx)
            if not cap.isOpened():
                logger.error(f"Failed to open camera {new_idx}")
            tracker.reset()

        t0 = time.perf_counter()
        ret, frame = cap.read()
        t1 = time.perf_counter()
        if not ret:
            time.sleep(0.01)
            continue

        params = state.get_tracker_params()
        if params['flip_horizontal']:
            frame = cv2.flip(frame, 1)

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

        t2 = time.perf_counter()
        _, jpeg = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), display_quality])
        t3 = time.perf_counter()

        t_capture += (t1 - t0) * 1000
        t_track   += (t2 - t1) * 1000
        t_encode  += (t3 - t2) * 1000
        timing_count += 1

        frame_count += 1
        now = time.time()
        elapsed = now - last_fps_time
        if elapsed >= 1.0:
            current_fps = round(frame_count / elapsed, 1)
            frame_count = 0
            last_fps_time = now

        if timing_count == _TIMING_INTERVAL:
            n = _TIMING_INTERVAL
            logger.info(
                f"[timing/{n}f avg] capture {t_capture/n:.1f}ms  "
                f"track {t_track/n:.1f}ms  encode {t_encode/n:.1f}ms  "
                f"total {(t_capture+t_track+t_encode)/n:.1f}ms"
            )
            timing_count = 0
            t_capture = t_track = t_encode = 0.0

        state.push_frame(jpeg.tobytes(), active, current_fps, warming_up, areas)

    logger.info("Camera loop stopped.")
