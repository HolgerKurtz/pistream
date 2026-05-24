import cv2
import zmq
import time
import numpy as np
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    port    = int(os.getenv('PORT', 5555))
    source  = os.getenv('MOCK_SOURCE', '0')
    width   = int(os.getenv('STREAM_WIDTH', 1280))
    height  = int(os.getenv('STREAM_HEIGHT', 720))
    quality = int(os.getenv('STREAM_QUALITY', 85))

    logger.info(f"Mock Streamer: port={port} source={source} resolution={width}×{height} quality={quality}")

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    try:
        socket.bind(f"tcp://*:{port}")
        logger.info(f"Mock Streamer started at tcp://*:{port}")
    except Exception as e:
        logger.error(f"Failed to bind ZMQ socket: {e}")
        return

    if source.isdigit():
        source = int(source)

    cap = None
    if source != 'noise':
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error(f"Could not open video source {source}")
            return

    frame_interval = 1.0 / 10  # 10 fps target
    try:
        while True:
            t_start = time.perf_counter()

            if source == 'noise':
                frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            else:
                ret, frame = cap.read()
                if not ret:
                    logger.info("End of stream, restarting...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

            # Resize only when the captured size differs from the target
            h, w = frame.shape[:2]
            if (w, h) != (width, height):
                frame = cv2.resize(frame, (width, height))

            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            socket.send(buffer)

            # Sleep only the remaining time to hit the target frame interval
            elapsed = time.perf_counter() - t_start
            remaining = frame_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        logger.info("Stopping mock streamer...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if cap:
            cap.release()
        socket.close()
        context.term()
        logger.info("Cleaned up resources.")

if __name__ == "__main__":
    main()
