import time
import zmq
import socket
import sys
import os
import logging
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try importing Picamera2
try:
    from picamera2 import Picamera2
    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput
except ImportError:
    logger.error("picamera2 module not found. This script is intended for Raspberry Pi with libcamera.")
    sys.exit(1)

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# A custom output that sends data via ZMQ
class ZmqOutput(io.BufferedIOBase):
    def __init__(self, socket):
        self.socket = socket

    def write(self, buf):
        # buf is the JPEG data
        # Send it directly via ZMQ
        self.socket.send(buf)
        return len(buf)

def main():
    # Get configuration from environment variables
    port = int(os.getenv('PORT', 5555))
    
    logger.info(f"Initializing Pi Streamer on port {port}...")

    # Initialize ZMQ
    try:
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind(f"tcp://*:{port}")
    except Exception as e:
        logger.error(f"Failed to bind ZMQ socket: {e}")
        sys.exit(1)
    
    ip = get_ip_address()
    logger.info(f"Streamer started at tcp://{ip}:{port}")

    # Initialize Picamera2
    try:
        picam2 = Picamera2()

        # Configure the camera
        # Low resolution and framerate for Pi Zero W
        video_config = picam2.create_video_configuration(
            main={"size": (640, 480)},
            lores={"size": (640, 480)},
            controls={"FrameRate": 15}
        )
        picam2.configure(video_config)
        
        # Create our ZMQ output wrapper
        zmq_output = ZmqOutput(socket)

        # Start recording using JpegEncoder
        picam2.start_recording(JpegEncoder(), FileOutput(zmq_output))
        logger.info("Camera recording started. Streaming data...")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopping streamer...")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        try:
            picam2.stop_recording()
            picam2.close()
        except Exception:
            pass
        socket.close()
        context.term()
        logger.info("Cleaned up resources.")

if __name__ == "__main__":
    main()
