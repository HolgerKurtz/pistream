import json
import os
import sys
import time
import logging
from urllib.parse import urlparse
from flask import Flask, Response, render_template, request, jsonify
from state import AppState

logger = logging.getLogger(__name__)

# Resolve template folder so it works both in development and as a frozen .app bundle
_here = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(_here, 'templates'))

_state: AppState
_sound_note_duration: float = 2.0


def init(state: AppState, config: dict = None) -> None:
    global _state, _sound_note_duration
    _state = state
    if config:
        _sound_note_duration = config.get('sound_note_duration', 2.0)


@app.route('/')
def index():
    return render_template('index.html', note_duration=_sound_note_duration)


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


def _is_local_origin(origin: str) -> bool:
    """Return True only for exact http://localhost or http://127.0.0.1 (any port)."""
    try:
        p = urlparse(origin)
        return p.scheme == 'http' and p.hostname in ('localhost', '127.0.0.1')
    except Exception:
        return False


@app.route('/control', methods=['POST'])
def control():
    # Require the custom header the UI always sends; cross-origin requests
    # cannot set custom headers without a CORS preflight (which we don't serve).
    if request.headers.get('X-Requested-With') != 'BirdsInTheSky':
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    # Defence-in-depth: if Origin is present, verify it is exactly localhost.
    origin = request.headers.get('Origin', '')
    if origin and not _is_local_origin(origin):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    data = request.get_json() or {}
    if not data:
        logger.warning("Empty or non-JSON /control payload")
        return jsonify({'ok': False, 'error': 'empty payload'}), 400
    _state.apply_control(data)
    return jsonify({'ok': True})
