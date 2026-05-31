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
    recalibrate_interval: float = 15.0,
) -> None:
    frame_count = 0
    last_fps_time = time.time()
    current_fps = 0.0
    prev_tracking = True
    needs_brightness_calibration = True  # calibrate on first live frame
    last_calibration_time = 0.0          # force immediate calibration on first active frame

    _TIMING_INTERVAL = 30
    timing_count = 0
    t_capture = t_track = t_encode = 0.0

    while not stop_event.is_set():
        t0 = time.perf_counter()
        ret, frame = cap.read()
        t1 = time.perf_counter()
        if not ret:
            time.sleep(0.01)
            continue

        now = time.time()
        params = state.get_tracker_params()
        if params['flip_horizontal']:
            frame = cv2.flip(frame, 1)

        resuming_tracking = not prev_tracking and params['tracking_active']
        if prev_tracking and not params['tracking_active']:
            tracker.reset()
        prev_tracking = params['tracking_active']

        if params['tracking_active']:
            tracker.sky_darkness_pct = params['sky_darkness_pct']  # recomputes brightness if pct changed
            tracker.trail_length = params['trail_length']
            tracker.trail_thickness = params['trail_thickness']

            due = now - last_calibration_time >= recalibrate_interval
            if needs_brightness_calibration or resuming_tracking or due:
                calibrated = tracker.calibrate_sky_brightness(frame)
                state.set_auto_brightness(calibrated)
                last_calibration_time = now
                needs_brightness_calibration = False

            results, annotated = tracker.process_frame(frame)
            active = len(results.tracks)
            warming_up = results.warming_up

            h, w = annotated.shape[:2]
            birds = []
            for obj_id, trail in results.tracks.items():
                if not trail:
                    continue
                cx, cy = trail[-1]
                birds.append({'id': obj_id, 'x': round(cx / w, 4), 'y': round(cy / h, 4)})
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            annotated = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            active = 0
            warming_up = False
            birds = []

        t2 = time.perf_counter()
        _, jpeg = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), display_quality])
        t3 = time.perf_counter()

        t_capture += (t1 - t0) * 1000
        t_track   += (t2 - t1) * 1000
        t_encode  += (t3 - t2) * 1000
        timing_count += 1

        frame_count += 1
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

        state.push_frame(jpeg.tobytes(), active, current_fps, warming_up, birds)

    logger.info("Camera loop stopped.")
