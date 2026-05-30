import logging
import threading
import time
import webbrowser

from config import get_config
from state import AppState
from bird_tracker import BirdTracker
import camera_loop
import web_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = get_config()

    camera_index = config['camera_index']

    tracker = BirdTracker(
        bg_history=config['bg_history'],
        bg_var_threshold=config['bg_var_threshold'],
        min_area=config['min_area'],
        max_area=config['max_area'],
        max_brightness=config['max_brightness'],
        max_match_distance=config['max_match_distance'],
        trail_length=config['trail_length'],
        trail_thickness=config['trail_thickness'],
        max_disappeared=config['max_disappeared'],
        warmup_frames=config['warmup_frames'],
        min_track_age=config['min_track_age'],
    )

    try:
        cap = camera_loop.initialize(camera_index)
    except RuntimeError as e:
        logger.error(e)
        return

    state = AppState(config)
    web_app.init(state)

    stop_event = threading.Event()
    cam_thread = threading.Thread(
        target=camera_loop.run,
        args=(cap, tracker, state, stop_event, config['display_quality'], config['recalibrate_interval']),
        daemon=True,
    )
    cam_thread.start()

    port = config['web_port']
    threading.Thread(
        target=lambda: (time.sleep(1.5), webbrowser.open(f"http://localhost:{port}")),
        daemon=True,
    ).start()

    logger.info(f"Web UI → http://localhost:{port}")
    try:
        web_app.app.run(
            host='0.0.0.0',
            port=port,
            threaded=True,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down…")
    finally:
        stop_event.set()
        cam_thread.join(timeout=2.0)
        cap.release()
        logger.info("Done.")


if __name__ == '__main__':
    main()
