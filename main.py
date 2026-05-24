import logging
import threading

from config import get_config
from state import AppState
from bird_tracker import BirdTracker
import zmq_loop
import web_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = get_config()
    logger.info(f"Config: {config}")

    tracker = BirdTracker(
        bg_history=config['bg_history'],
        bg_var_threshold=config['bg_var_threshold'],
        min_area=config['min_area'],
        max_area=config['max_area'],
        trail_length=config['trail_length'],
        max_disappeared=config['max_disappeared'],
        warmup_frames=config['warmup_frames'],
        min_track_age=config['min_track_age'],
    )

    try:
        context, socket = zmq_loop.initialize(config['host'], config['port'])
    except Exception as e:
        logger.error(f"Cannot connect to stream: {e}")
        return

    state = AppState(config)
    web_app.init(state)

    stop_event = threading.Event()
    zmq_thread = threading.Thread(
        target=zmq_loop.run,
        args=(socket, tracker, state, stop_event, config['display_quality']),
        daemon=True,
    )
    zmq_thread.start()

    logger.info(f"Web UI → http://localhost:{config['web_port']}")
    try:
        web_app.app.run(
            host='0.0.0.0',
            port=config['web_port'],
            threaded=True,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down…")
    finally:
        stop_event.set()
        zmq_thread.join(timeout=2.0)
        socket.close()
        context.term()
        logger.info("Done.")


if __name__ == '__main__':
    main()
