import cv2
import zmq
import numpy as np
import os
import logging
from dotenv import load_dotenv
from vision_processor import VisionProcessor
from music_generator import MusicGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_config():
    """Retrieve configuration from environment variables."""
    return {
        'host': os.getenv('PI_IP', 'localhost'),
        'port': int(os.getenv('PORT', 5555)),
        'model_name': os.getenv('MODEL', 'yolo11n.pt'),
        'task': os.getenv('TASK', 'detect'),
        'headless': os.getenv('HEADLESS', 'False').lower() == 'true'
    }

def initialize_zmq(host, port):
    """Initialize and connect the ZMQ subscriber socket."""
    try:
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(f"tcp://{host}:{port}")
        socket.setsockopt_string(zmq.SUBSCRIBE, '')
        logger.info(f"ZMQ socket connected to tcp://{host}:{port}")
        return context, socket
    except Exception as e:
        logger.error(f"Failed to connect ZMQ socket: {e}")
        raise

def receive_frame(socket):
    """Receive and decode a frame from the ZMQ socket."""
    try:
        buffer = socket.recv()
        np_arr = np.frombuffer(buffer, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return frame
    except zmq.ZMQError as e:
        logger.error(f"ZMQ receive error: {e}")
        return None
    except Exception as e:
        logger.error(f"Frame decoding error: {e}")
        return None

def process_stream(socket, processor, music_generator, headless):
    """Main loop to receive, process, and display frames."""
    try:
        while True:
            frame = receive_frame(socket)
            
            if frame is None:
                logger.warning("Received empty or invalid frame, skipping...")
                continue

            # Mirror frame (horizontal flip)
            frame = cv2.flip(frame, 1)

            # Process frame
            results, annotated_frame = processor.process_frame(frame)

            # Generate Music
            if music_generator and results and hasattr(results, 'keypoints'):
                music_generator.process_pose(results.keypoints)

            if not headless:
                cv2.imshow("YOLO Inference", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        logger.info("Stopping inference server...")
    except Exception as e:
        logger.error(f"An unexpected error occurred in stream loop: {e}")
    finally:
        if not headless:
            cv2.destroyAllWindows()

def main():
    config = get_config()
    
    logger.info(f"Starting Server Inference with config: {config}")

    # Initialize Vision Processor
    try:
        processor = VisionProcessor(model_name=config['model_name'], task=config['task'])
    except Exception:
        logger.error("Failed to initialize VisionProcessor. Exiting.")
        return

    # Initialize ZMQ
    try:
        context, socket = initialize_zmq(config['host'], config['port'])
    except Exception:
        return

    # Initialize Music Generator
    music_generator = None
    if config['task'] == 'pose':
        try:
            music_generator = MusicGenerator()
        except Exception as e:
            logger.error(f"Failed to initialize MusicGenerator: {e}")

    # Run Main Loop
    try:
        process_stream(socket, processor, music_generator, config['headless'])
    finally:
        if music_generator:
            music_generator.close()
        socket.close()
        context.term()
        logger.info("Cleaned up resources.")

if __name__ == "__main__":
    main()
