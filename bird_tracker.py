import cv2
import numpy as np
import logging
from collections import deque, OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


@dataclass
class BirdResults:
    tracks: Dict[int, deque]                    # id -> deque of (cx, cy) — confirmed tracks only
    boxes: List[Tuple[int, int, int, int]]       # list of (x, y, w, h)
    centroids: List[Tuple[int, int]]
    warming_up: bool                             # True during initial background learning
    detection_areas: List[int]                  # pixel areas of all blobs that passed the size filter


class BirdTracker:
    def __init__(
        self,
        bg_history: int = 500,
        bg_var_threshold: float = 16.0,
        min_area: int = 20,
        max_area: int = 2000,
        trail_length: int = 60,
        max_disappeared: int = 10,
        warmup_frames: int = 60,
        min_track_age: int = 4,
    ):
        self.min_area = min_area
        self.max_area = max_area
        self.trail_length = trail_length
        self.max_disappeared = max_disappeared
        self.warmup_frames = warmup_frames
        self.min_track_age = min_track_age

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=bg_history,
            varThreshold=bg_var_threshold,
            detectShadows=False,
        )

        self._kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self._kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        self._frame_count = 0
        self._next_id = 0
        self._tracks: Dict[int, deque] = OrderedDict()
        self._disappeared: Dict[int, int] = OrderedDict()
        self._boxes: Dict[int, Tuple[int, int, int, int]] = {}
        self._ages: Dict[int, int] = {}  # id -> total frames seen

        logger.info(
            f"BirdTracker initialized (min_area={min_area}, max_area={max_area}, "
            f"trail={trail_length}, max_disappeared={max_disappeared}, "
            f"warmup={warmup_frames}, min_track_age={min_track_age})"
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def process_frame(self, frame: np.ndarray) -> Tuple[BirdResults, np.ndarray]:
        self._frame_count += 1
        warming_up = self._frame_count <= self.warmup_frames

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Use a high learning rate during warm-up so MOG2 learns the
        # background quickly; after that let it adapt at its natural pace.
        learning_rate = 0.5 if warming_up else -1
        fg_mask = self.bg_subtractor.apply(gray, learningRate=learning_rate)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self._kernel_open)
        fg_mask = cv2.dilate(fg_mask, self._kernel_dilate, iterations=1)

        centroids: List[Tuple[int, int]] = []
        boxes: List[Tuple[int, int, int, int]] = []
        areas: List[int] = []

        if not warming_up:
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = int(cv2.contourArea(cnt))
                if not (self.min_area <= area <= self.max_area):
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                centroids.append((x + w // 2, y + h // 2))
                boxes.append((x, y, w, h))
                areas.append(area)

        self._update_tracks(centroids, boxes)

        # Only expose tracks that have been alive long enough to be real birds
        confirmed = {
            obj_id: trail
            for obj_id, trail in self._tracks.items()
            if self._ages.get(obj_id, 0) >= self.min_track_age
        }
        confirmed_boxes = [
            self._boxes[obj_id] for obj_id in confirmed if obj_id in self._boxes
        ]

        annotated = self._annotate(gray, confirmed, warming_up)
        results = BirdResults(
            tracks=confirmed,
            boxes=confirmed_boxes,
            centroids=centroids,
            warming_up=warming_up,
            detection_areas=areas,
        )
        return results, annotated

    def reset(self) -> None:
        """Clear all tracks and restart IDs from 0. Called when tracking is paused."""
        self._next_id = 0
        self._tracks.clear()
        self._disappeared.clear()
        self._boxes.clear()
        self._ages.clear()
        logger.info("BirdTracker state reset.")

    # ------------------------------------------------------------------
    # Centroid tracker
    # ------------------------------------------------------------------

    def _update_tracks(
        self,
        centroids: List[Tuple[int, int]],
        boxes: List[Tuple[int, int, int, int]],
    ):
        if not self._tracks:
            for c, b in zip(centroids, boxes):
                self._register(c, b)
            return

        if not centroids:
            for obj_id in list(self._disappeared):
                self._disappeared[obj_id] += 1
                if self._disappeared[obj_id] > self.max_disappeared:
                    self._deregister(obj_id)
            return

        existing_ids = list(self._tracks.keys())
        existing_centroids = [self._tracks[i][-1] for i in existing_ids]

        D = np.linalg.norm(
            np.array(existing_centroids)[:, None] - np.array(centroids)[None, :],
            axis=2,
        )

        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        used_rows, used_cols = set(), set()
        for r, c in zip(rows, cols):
            if r in used_rows or c in used_cols:
                continue
            obj_id = existing_ids[r]
            self._tracks[obj_id].append(centroids[c])
            self._boxes[obj_id] = boxes[c]
            self._disappeared[obj_id] = 0
            self._ages[obj_id] = self._ages.get(obj_id, 0) + 1
            used_rows.add(r)
            used_cols.add(c)

        for r in range(len(existing_ids)):
            if r not in used_rows:
                obj_id = existing_ids[r]
                self._disappeared[obj_id] += 1
                if self._disappeared[obj_id] > self.max_disappeared:
                    self._deregister(obj_id)

        for c in range(len(centroids)):
            if c not in used_cols:
                self._register(centroids[c], boxes[c])

    def _register(self, centroid: Tuple[int, int], box: Tuple[int, int, int, int]):
        trail = deque(maxlen=self.trail_length)
        trail.append(centroid)
        self._tracks[self._next_id] = trail
        self._boxes[self._next_id] = box
        self._disappeared[self._next_id] = 0
        self._ages[self._next_id] = 1
        self._next_id += 1

    def _deregister(self, obj_id: int):
        del self._tracks[obj_id]
        del self._disappeared[obj_id]
        self._boxes.pop(obj_id, None)
        self._ages.pop(obj_id, None)

    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------

    def _annotate(
        self,
        gray: np.ndarray,
        confirmed: Dict[int, deque],
        warming_up: bool,
    ) -> np.ndarray:
        display = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        if warming_up:
            pct = int(self._frame_count / self.warmup_frames * 100)
            cv2.putText(
                display, f"Calibrating background… {pct}%",
                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 180, 255), 1, cv2.LINE_AA,
            )
            return display

        for obj_id, trail in confirmed.items():
            if not trail:
                continue

            color = self._id_color(obj_id)
            pts = list(trail)
            n = len(pts)

            for i in range(1, n):
                alpha = i / n
                thickness = max(1, int(alpha * 3))
                c = tuple(int(v * alpha) for v in color)
                cv2.line(display, pts[i - 1], pts[i], c, thickness)

            if self._disappeared.get(obj_id, 1) == 0 and obj_id in self._boxes:
                x, y, w, h = self._boxes[obj_id]
                cv2.rectangle(display, (x, y), (x + w, y + h), color, 1)

            cx, cy = pts[-1]
            cv2.putText(
                display, str(obj_id), (cx + 4, cy - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA,
            )

        return display

    @staticmethod
    def _id_color(obj_id: int) -> Tuple[int, int, int]:
        hue = int((obj_id * 47) % 180)
        hsv = np.uint8([[[hue, 255, 220]]])
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
        return int(bgr[0]), int(bgr[1]), int(bgr[2])
