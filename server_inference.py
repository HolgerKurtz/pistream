import cv2
import zmq
import numpy as np
from ultralytics import YOLO
import argparse

def main():
    parser = argparse.ArgumentParser(description='Server Inference')
    parser.add_argument('--host', type=str, default='localhost', help='IP of the streamer')
    parser.add_argument('--port', type=int, default=5555, help='Port of the streamer')
    parser.add_argument('--model', type=str, default='yolov8n.pt', help='YOLO model to use')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode (no GUI)')
    args = parser.parse_args()

    # Initialize YOLO model
    print(f"Loading model {args.model}...")
    model = YOLO(args.model)

    # Initialize ZMQ subscriber
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://{args.host}:{args.port}")
    socket.setsockopt_string(zmq.SUBSCRIBE, '')
    print(f"Connected to stream at tcp://{args.host}:{args.port}")

    try:
        while True:
            # Receive frame data
            buffer = socket.recv()
            
            # Decode image
            np_arr = np.frombuffer(buffer, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                print("Received empty frame")
                continue

            # Run inference
            results = model.track(frame, persist=True)

            # Visualize results
            annotated_frame = results[0].plot()

            if args.headless:
                # Just log that we processed a frame
                print(f"Processed frame with {len(results[0].boxes)} detections")
            else:
                # Display
                cv2.imshow("YOLOv8 Inference", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        socket.close()
        context.term()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
