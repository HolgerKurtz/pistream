import cv2
import zmq
import socket
import time
import argparse

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

def main():
    parser = argparse.ArgumentParser(description='Pi Streamer')
    parser.add_argument('--port', type=int, default=5555, help='Port to bind to')
    args = parser.parse_args()

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    # We bind to all interfaces
    socket.bind(f"tcp://*:{args.port}")
    
    ip = get_ip_address()
    print(f"Streamer started at tcp://{ip}:{args.port}")

    # Initialize camera
    # Using OpenCV's VideoCapture which works with libcamera on newer Pi OS if configured correctly
    # or legacy stack. For Pi Zero W, we want low resolution/fps for performance.
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 10)

    if not cap.isOpened():
        print("Error: Could not open video device.")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            # Compress frame to reduce bandwidth
            # JPEG quality 80
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            
            # Send data
            socket.send(buffer)
            
            # Optional: Sleep to strictly limit FPS if needed, but capture limit should handle it
            # time.sleep(0.05) 

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        cap.release()
        socket.close()
        context.term()

if __name__ == "__main__":
    main()
