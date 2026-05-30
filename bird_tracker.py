import cv2
import numpy as np
import logging
from collections import deque, OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def _dist(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


@dataclass
class BirdResults:
    tracks: Dict[int, deque]              # id -> deque of (cx, cy) — confirmed tracks only
    boxes: List[Tuple[int, int, int, int]]
    centroids: List[Tuple[int, int]]
    warming_up: bool


class BirdTracker:
    def __init__(
        self,
        bg_history: int = 500,
        bg_var_threshold: float = 16.0,
        min_area: int = 20,
        max_area: int = 2000,
        trail_length: int = 60,
        trail_thickness: int = 3,
        max_disappeared: int = 10,
        warmup_frames: int = 60,
        min_track_age: int = 4,
        max_brightness: int = 120,
        max_match_distance: int = 150,
    ):
        self.min_area = min_area
        self.max_area = max_area
        self.max_brightness = max_brightness
        self.max_match_distance = max_match_distance
        self._trail_length = trail_length
        self.trail_thickness = trail_thickness
        self.max_disappeared = max_disappeared
        self.warmup_frames = warmup_frames
        self.min_track_age = min_track_age

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=bg_history,
            varThreshold=bg_var_threshold,
            detectShadows=False,
        )

        self._kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        self._sky_mean: int = 0
        self._sky_darkness_pct: int = 25

        self._frame_count = 0
        self._next_id = 0
        self._tracks: Dict[int, deque] = OrderedDict()
        self._disappeared: Dict[int, int] = OrderedDict()
        self._boxes: Dict[int, Tuple[int, int, int, int]] = {}
        self._ages: Dict[int, int] = {}  # id -> total frames seen

        logger.info(
            f"BirdTracker initialized (min_area={min_area}, max_area={max_area}, "
            f"max_brightness={max_brightness}, trail={trail_length}×{trail_thickness}px, "
            f"max_disappeared={max_disappeared}, warmup={warmup_frames}, "
            f"min_track_age={min_track_age})"
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def trail_length(self) -> int:
        return self._trail_length

    @trail_length.setter
    def trail_length(self, value: int) -> None:
        if value == self._trail_length:
            return
        self._trail_length = value
        for obj_id, old in list(self._tracks.items()):
            self._tracks[obj_id] = deque(old, maxlen=value)

    @property
    def sky_darkness_pct(self) -> int:
        return self._sky_darkness_pct

    @sky_darkness_pct.setter
    def sky_darkness_pct(self, value: int) -> None:
        if value == self._sky_darkness_pct:
            return
        self._sky_darkness_pct = value
        if self._sky_mean > 0:
            threshold = max(20, min(220, int(self._sky_mean * (1 - value / 100))))
            self.max_brightness = threshold
            logger.info(f"max_brightness updated to {threshold} (sky_mean={self._sky_mean}, darkness={value}%)")

    # MOG2 and contour detection run at this fraction of the capture resolution.
    # 0.5 → 640×360 on a 1280×720 source: ~4× fewer pixels, ~4× faster.
    _PROC_SCALE: float = 0.5

    def process_frame(self, frame: np.ndarray) -> Tuple[BirdResults, np.ndarray]:
        self._frame_count += 1
        warming_up = self._frame_count <= self.warmup_frames

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Downscale for MOG2 and contour detection; keep full-res gray for annotation.
        scale = self._PROC_SCALE
        proc = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        learning_rate = 0.5 if warming_up else -1
        fg_mask = self.bg_subtractor.apply(proc, learningRate=learning_rate)
        fg_mask_raw = fg_mask  # pre-dilate: marks exactly the moving pixels, used for brightness sampling
        fg_mask = cv2.dilate(fg_mask, self._kernel_dilate, iterations=1)

        centroids: List[Tuple[int, int]] = []
        boxes: List[Tuple[int, int, int, int]] = []

        if not warming_up:
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            inv = 1.0 / scale
            area_inv = inv * inv  # contour areas are in proc pixels²; scale to full-res px²
            for cnt in contours:
                area_fr = int(cv2.contourArea(cnt) * area_inv)
                if not (self.min_area <= area_fr <= self.max_area):
                    continue
                px, py, pw, ph = cv2.boundingRect(cnt)
                # Sample brightness from the actual moving pixels (pre-dilate mask, proc scale).
                # The dilated bounding box is mostly sky padding; fg_mask_raw isolates the bird pixels.
                fg_crop = fg_mask_raw[py:py + ph, px:px + pw]
                proc_crop = proc[py:py + ph, px:px + pw]
                bird_pixels = proc_crop[fg_crop > 0]
                mean_brightness = int(np.mean(bird_pixels)) if bird_pixels.size > 0 else 128
                # Map bounding rect back to full-res coordinates for centroid & box output
                fx = int(round(px * inv))
                fy = int(round(py * inv))
                fw = int(round(pw * inv))
                fh = int(round(ph * inv))
                if mean_brightness > self.max_brightness:
                    continue
                centroids.append((fx + fw // 2, fy + fh // 2))
                boxes.append((fx, fy, fw, fh))

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
        )
        return results, annotated

    def calibrate_sky_brightness(self, frame: np.ndarray) -> int:
        """
        Measure sky brightness and set max_brightness = sky_mean × (1 - sky_darkness_pct/100).
        Dark outliers (trees < 40) and blown-out highlights (> 245) are excluded.
        Returns the new max_brightness value.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        sky_pixels = gray[(gray > 40) & (gray < 245)]
        if sky_pixels.size < 1000:
            logger.warning("Too few sky pixels for brightness calibration — keeping current value")
            return self.max_brightness
        self._sky_mean = int(np.mean(sky_pixels))
        threshold = max(20, min(220, int(self._sky_mean * (1 - self._sky_darkness_pct / 100))))
        self.max_brightness = threshold
        logger.info(
            f"Brightness calibrated: sky_mean={self._sky_mean} → max_brightness={threshold} "
            f"(darkness={self._sky_darkness_pct}%)"
        )
        return threshold

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
            if D[r, c] > self.max_match_distance:
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
                if _dist(pts[i - 1], pts[i]) > self.max_match_distance:
                    continue
                alpha = i / n
                thickness = max(1, int(alpha * self.trail_thickness))
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
