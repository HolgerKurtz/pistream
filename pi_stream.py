import time
import zmq
import socket
import argparse
import sys

# Try importing Picamera2
try:
    from picamera2 import Picamera2
    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput
except ImportError:
    print("Error: picamera2 module not found. This script is intended for Raspberry Pi with libcamera.")
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

import io

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
    parser = argparse.ArgumentParser(description='Pi Streamer (Picamera2 + ZMQ)')
    parser.add_argument('--port', type=int, default=5555, help='Port to bind to')
    args = parser.parse_args()

    # Initialize ZMQ
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{args.port}")
    
    ip = get_ip_address()
    print(f"Streamer started at tcp://{ip}:{args.port}")

    # Initialize Picamera2
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
    # This uses the hardware JPEG encoder (if available) or optimized software encoder
    picam2.start_recording(JpegEncoder(), FileOutput(zmq_output))

    print("Streaming...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        picam2.stop_recording()
        picam2.close()
        socket.close()
        context.term()

if __name__ == "__main__":
    main()
