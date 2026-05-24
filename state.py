import threading
from typing import List, Optional


class AppState:
    """
    Shared state between the camera loop and the Flask web server.
    All public methods acquire the internal lock, so callers never need to.
    """

    def __init__(self, config: dict, camera_list: List[dict]):
        self._lock = threading.Lock()

        # Frame output (written by camera loop, read by Flask)
        self._latest_frame: Optional[bytes] = None
        self._active_tracks: int = 0
        self._fps: float = 0.0
        self._warming_up: bool = True
        self._detection_areas: List[int] = []

        # Tunable params (written by Flask /control, read by camera loop)
        self._tracking_active: bool = True
        self._flip_horizontal: bool = config.get('flip_horizontal', False)
        self._min_area: int = config['min_area']
        self._max_area: int = config['max_area']
        self._bg_var_threshold: float = config['bg_var_threshold']
        self._min_track_age: int = config['min_track_age']

        # Camera selection
        self._camera_list: List[dict] = camera_list
        self._camera_index: int = config.get('camera_index', 0)
        self._camera_changed: bool = False

    # ------------------------------------------------------------------
    # Camera loop → Flask  (camera loop writes, Flask reads)
    # ------------------------------------------------------------------

    def push_frame(
        self,
        jpeg: bytes,
        active_tracks: int,
        fps: float,
        warming_up: bool,
        detection_areas: Optional[List[int]] = None,
    ) -> None:
        with self._lock:
            self._latest_frame = jpeg
            self._active_tracks = active_tracks
            self._fps = fps
            self._warming_up = warming_up
            self._detection_areas = detection_areas or []

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
                'min_area':         self._min_area,
                'max_area':         self._max_area,
                'bg_var_threshold': self._bg_var_threshold,
                'min_track_age':    self._min_track_age,
                'blob_area_min':    min(self._detection_areas) if self._detection_areas else None,
                'blob_area_max':    max(self._detection_areas) if self._detection_areas else None,
                'camera_index':     self._camera_index,
            }

    def get_camera_list(self) -> List[dict]:
        with self._lock:
            return list(self._camera_list)

    # ------------------------------------------------------------------
    # Flask → camera loop  (Flask writes, camera loop reads)
    # ------------------------------------------------------------------

    def get_tracker_params(self) -> dict:
        """Consistent snapshot so the camera loop reads all params under one lock."""
        with self._lock:
            return {
                'tracking_active':  self._tracking_active,
                'flip_horizontal':  self._flip_horizontal,
                'min_area':         self._min_area,
                'max_area':         self._max_area,
                'bg_var_threshold': self._bg_var_threshold,
                'min_track_age':    self._min_track_age,
                'camera_index':     self._camera_index,
            }

    def pop_camera_changed(self) -> Optional[int]:
        """Returns the new camera index if it changed since last call, else None."""
        with self._lock:
            if self._camera_changed:
                self._camera_changed = False
                return self._camera_index
            return None

    def apply_control(self, data: dict) -> None:
        """Update tunable params from the web /control endpoint."""
        with self._lock:
            if 'tracking' in data:
                self._tracking_active = bool(data['tracking'])
            if 'flip_horizontal' in data:
                self._flip_horizontal = bool(data['flip_horizontal'])
            if 'min_area' in data:
                self._min_area = int(data['min_area'])
            if 'max_area' in data:
                self._max_area = int(data['max_area'])
            if 'bg_var_threshold' in data:
                self._bg_var_threshold = float(data['bg_var_threshold'])
            if 'min_track_age' in data:
                self._min_track_age = int(data['min_track_age'])
            if 'camera_index' in data:
                new_idx = int(data['camera_index'])
                if new_idx != self._camera_index:
                    self._camera_index = new_idx
                    self._camera_changed = True
