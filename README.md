# PISTREAM

A lightweight, split-architecture motion detection and object tracking system designed for the Raspberry Pi Zero W.

## Overview

This project uses a **Split Architecture** to overcome the limited processing power of the Raspberry Pi Zero W.
*   **Edge (Raspberry Pi)**: Captures video and streams it efficiently over the network.
*   **Server (PC/Cloud)**: Receives the stream and performs heavy-duty object detection using YOLOv8.

## Architecture

```mermaid
graph LR
    A[Raspberry Pi Zero W] -- ZMQ Stream (JPEG) --> B[Server / Cloud]
    B -- Inference --> C[YOLOv8]
    C -- Output --> D[Display / Log]
```

### Components

*   **`pi_stream.py`**: Runs on the Raspberry Pi. Uses `Picamera2` to capture video and `ZMQ` to stream JPEG frames.
*   **`server_inference.py`**: Runs on a powerful machine. Connects to the Pi's ZMQ stream, decodes frames, and runs YOLOv8 tracking.
*   **`mock_stream.py`**: A utility for testing. Mimics the Pi's ZMQ stream (from webcam, file, or noise).

## Installation

We use `uv` for fast dependency management.

1.  **Clone the repository**:
    ```bash
    git clone <repo_url>
    cd pistream
    ```

2.  **Setup Environment**:
    ```bash
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
    ```

## Usage

### 1. Start the Streamer (Edge)

**On the Raspberry Pi:**
Transfer `pi_stream.py` and `requirements-pi.txt` to the Pi.

Install dependencies:
```bash
pip install -r requirements-pi.txt
```
*Note: `picamera2` is usually pre-installed on Raspberry Pi OS. If not, install via `sudo apt install python3-picamera2`.*

Run the streamer:
```bash
python3 pi_stream.py --port 5555
```

**Local Testing (Mock):**
To simulate a stream from your webcam:
```bash
python3 mock_stream.py --source 0
```
To simulate with noise (no camera needed):
```bash
python3 mock_stream.py --source noise
```

### 2. Start the Inference Server

**On your Server/Mac:**
```bash
python3 server_inference.py --host <PI_IP_OR_LOCALHOST> --port 5555
```

**Options:**
*   `--headless`: Run without a GUI window (useful for cloud/headless servers).
*   `--model`: Specify a different YOLO model (default: `yolov8n.pt`).

## Development

*   **Requirements**: `ultralytics`, `opencv-python`, `zmq`, `imutils`, `lapx`.
*   **Protocol**: ZMQ PUB/SUB pattern. Frames are JPEG encoded.

## Troubleshooting

### Pi Zero: "picam2 module not found"
Ensure you are running on a Raspberry Pi with the latest OS (Bookworm or newer) and that `libcamera` is installed and working (`libcamera-hello`).
1.  Run `sudo raspi-config`
2.  Go to **Performance Options** -> **GPU Memory**
3.  Set it to **128** (or higher)
4.  Reboot the Pi.