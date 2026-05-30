import threading
from typing import Optional


class AppState:
    """
    Shared state between the camera loop and the Flask web server.
    All public methods acquire the internal lock, so callers never need to.
    """

    def __init__(self, config: dict):
        self._lock = threading.Lock()

        # Frame output (written by camera loop, read by Flask)
        self._latest_frame: Optional[bytes] = None
        self._active_tracks: int = 0
        self._fps: float = 0.0
        self._warming_up: bool = True

        # Live-tunable params (written by Flask /control or auto-calibration, read by camera loop)
        self._tracking_active: bool = True
        self._flip_horizontal: bool = config.get('flip_horizontal', False)
        self._max_brightness: int = config['max_brightness']   # overwritten by auto-calibration
        self._trail_length: int = config['trail_length']
        self._trail_thickness: int = config['trail_thickness']
        self._sky_darkness_pct: int = config.get('sky_darkness_pct', 25)

    # ------------------------------------------------------------------
    # Camera loop → Flask  (camera loop writes, Flask reads)
    # ------------------------------------------------------------------

    def push_frame(self, jpeg: bytes, active_tracks: int, fps: float, warming_up: bool) -> None:
        with self._lock:
            self._latest_frame = jpeg
            self._active_tracks = active_tracks
            self._fps = fps
            self._warming_up = warming_up

    def get_frame(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_frame

    def get_stats(self) -> dict:
        with self._lock:
            return {
                'active_tracks':    self._active_tracks,
                'tracking':         self._tracking_active,
                'flip_horizontal':  self._flip_horizontal,
                'warming_up':       self._warming_up,
                'fps':              self._fps,
                'trail_length':     self._trail_length,
                'trail_thickness':  self._trail_thickness,
                'sky_darkness_pct': self._sky_darkness_pct,
            }

    # ------------------------------------------------------------------
    # Flask → camera loop  (Flask writes, camera loop reads)
    # ------------------------------------------------------------------

    def get_tracker_params(self) -> dict:
        """Consistent snapshot so the camera loop reads all params under one lock."""
        with self._lock:
            return {
                'tracking_active':  self._tracking_active,
                'flip_horizontal':  self._flip_horizontal,
                'max_brightness':   self._max_brightness,
                'trail_length':     self._trail_length,
                'trail_thickness':  self._trail_thickness,
                'sky_darkness_pct': self._sky_darkness_pct,
            }

    def set_auto_brightness(self, value: int) -> None:
        """Called by the camera loop after sky auto-calibration."""
        with self._lock:
            self._max_brightness = value

    def apply_control(self, data: dict) -> None:
        """Update tunable params from the web /control endpoint."""
        with self._lock:
            if 'tracking' in data:
                self._tracking_active = bool(data['tracking'])
            if 'flip_horizontal' in data:
                self._flip_horizontal = bool(data['flip_horizontal'])
            if 'trail_length' in data:
                self._trail_length = max(1, min(1000, int(data['trail_length'])))
            if 'trail_thickness' in data:
                self._trail_thickness = max(1, min(20, int(data['trail_thickness'])))
            if 'sky_darkness_pct' in data:
                self._sky_darkness_pct = max(1, min(95, int(data['sky_darkness_pct'])))
