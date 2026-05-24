import json
import os
import sys
import time
import logging
from flask import Flask, Response, render_template, request, jsonify
from state import AppState

logger = logging.getLogger(__name__)

# Resolve template folder so it works both in development and as a frozen .app bundle
_here = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(_here, 'templates'))

_state: AppState


def init(state: AppState) -> None:
    global _state
    _state = state


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/cameras')
def cameras():
    return jsonify(_state.get_camera_list())


@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            frame = _state.get_frame()
            if frame:
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            time.sleep(0.04)  # cap browser delivery at ~25 fps

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/stats')
def stats_sse():
    def generate():
        while True:
            yield f'data: {json.dumps(_state.get_stats())}\n\n'
            time.sleep(0.4)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@app.route('/control', methods=['POST'])
def control():
    data = request.get_json(force=True) or {}
    if not data:
        logger.warning("Empty or unparseable /control payload")
        return jsonify({'ok': False, 'error': 'empty payload'}), 400
    _state.apply_control(data)
    return jsonify({'ok': True})
