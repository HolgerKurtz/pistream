import cv2
import zmq
import time
import numpy as np
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Get configuration from environment variables
    port = int(os.getenv('PORT', 5555))
    source = os.getenv('MOCK_SOURCE', '0') # Default to webcam 0

    logger.info(f"Initializing Mock Streamer on port {port} with source {source}...")

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    try:
        socket.bind(f"tcp://*:{port}")
        logger.info(f"Mock Streamer started at tcp://*:{port}")
    except Exception as e:
        logger.error(f"Failed to bind ZMQ socket: {e}")
        return

    # Handle numeric source for webcam
    if source.isdigit():
        source = int(source)

    cap = None
    if source != 'noise':
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error(f"Error: Could not open video source {source}")
            return

    try:
        while True:
            if source == 'noise':
                # Generate random noise frame
                frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                ret = True
            else:
                ret, frame = cap.read()
                if not ret:
                    logger.info("End of stream, restarting...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

            # Resize to match Pi Zero expectations (optional but good for simulation)
            frame = cv2.resize(frame, (640, 480))

            # Compress frame
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            
            # Send data
            socket.send(buffer)
            
            # Simulate 10 FPS
            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("Stopping mock streamer...")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        if cap:
            cap.release()
        socket.close()
        context.term()
        logger.info("Cleaned up resources.")

if __name__ == "__main__":
    main()
