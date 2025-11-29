import cv2
import zmq
import numpy as np
from ultralytics import YOLO
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
    host = os.getenv('PI_IP', 'localhost')
    port = int(os.getenv('PORT', 5555))
    model_name = os.getenv('MODEL', 'yolo11n.pt')
    headless = os.getenv('HEADLESS', 'False').lower() == 'true'

    logger.info(f"Connecting to streamer at tcp://{host}:{port}")
    logger.info(f"Using model: {model_name}")
    logger.info(f"Headless mode: {headless}")

    # Initialize YOLO model
    try:
        model = YOLO(model_name)
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        return

    # Initialize ZMQ subscriber
    try:
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(f"tcp://{host}:{port}")
        socket.setsockopt_string(zmq.SUBSCRIBE, '')
        logger.info("ZMQ socket connected.")
    except Exception as e:
        logger.error(f"Failed to connect ZMQ socket: {e}")
        return

    try:
        while True:
            # Receive frame data
            try:
                buffer = socket.recv()
            except zmq.ZMQError as e:
                logger.error(f"ZMQ receive error: {e}")
                break
            
            # Decode image
            np_arr = np.frombuffer(buffer, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                logger.warning("Received empty frame")
                continue

            # Run inference
            results = model.track(frame, persist=True, verbose=False)

            # Visualize results
            annotated_frame = results[0].plot()

            if headless:
                # Just log that we processed a frame
                # logger.info(f"Processed frame with {len(results[0].boxes)} detections")
                pass # Reduce log spam
            else:
                # Display
                cv2.imshow("YOLOv8 Inference", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        logger.info("Stopping inference server...")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        socket.close()
        context.term()
        cv2.destroyAllWindows()
        logger.info("Cleaned up resources.")

if __name__ == "__main__":
    main()
