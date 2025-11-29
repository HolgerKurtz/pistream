import cv2
import zmq
import time
import argparse
import numpy as np

def main():
    parser = argparse.ArgumentParser(description='Mock Streamer')
    parser.add_argument('--port', type=int, default=5555, help='Port to bind to')
    parser.add_argument('--source', type=str, default='0', help='Video source (0 for webcam, or path to file)')
    args = parser.parse_args()

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{args.port}")
    print(f"Mock Streamer started at tcp://*:{args.port}")

    # Handle numeric source for webcam
    source = args.source
    if source.isdigit():
        source = int(source)

    cap = None
    if source != 'noise':
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"Error: Could not open video source {source}")
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
                    print("End of stream, restarting...")
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
        print("Stopping...")
    finally:
        if cap:
            cap.release()
        socket.close()
        context.term()

if __name__ == "__main__":
    main()
