from ultralytics import YOLO
import logging

logger = logging.getLogger(__name__)

class VisionProcessor:
    def __init__(self, model_name='yolo11n.pt', task='detect'):
        """
        Initialize the VisionProcessor.
        
        Args:
            model_name (str): Path or name of the YOLO model.
            task (str): The task to perform ('detect', 'segment', 'pose', 'classify', 'track').
        """
        self.model_name = model_name
        self.task = task.lower()
        self.model = None
        
        self._load_model()

    def _load_model(self):
        try:
            logger.info(f"Loading model {self.model_name} for task '{self.task}'...")
            self.model = YOLO(self.model_name)
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise

    def process_frame(self, frame):
        """
        Process a single frame based on the configured task.
        
        Args:
            frame (numpy.ndarray): The input image frame.
            
        Returns:
            tuple: (results object, annotated_frame)
        """
        if self.model is None:
            return None, frame

        try:
            # Common arguments for most tasks
            # persist=True is crucial for tracking to maintain ID across frames
            kwargs = {'verbose': False}
            
            if self.task == 'track':
                results = self.model.track(frame, persist=True, **kwargs)
            elif self.task in ['detect', 'segment', 'pose']:
                # For these tasks, we can also use track() if we want ID persistence,
                # or predict() if we just want per-frame results.
                # Using track() is generally more useful for video streams.
                results = self.model.track(frame, persist=True, **kwargs)
            elif self.task == 'classify':
                results = self.model.predict(frame, **kwargs)
            else:
                logger.warning(f"Unknown task '{self.task}', defaulting to predict()")
                results = self.model.predict(frame, **kwargs)

            # Generate annotated frame
            # plot() handles drawing boxes, masks, keypoints, etc. automatically
            annotated_frame = results[0].plot()
            
            return results[0], annotated_frame

        except Exception as e:
            logger.error(f"Inference error: {e}")
            return None, frame
