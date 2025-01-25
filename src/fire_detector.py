import cv2
import numpy as np
from ultralytics import YOLO
import cvzone
import logging
from pathlib import Path


class Detector:
    def __init__(self, model_path: Path, target_height: int = 640):
        """
        Initialize the FireDetector with a YOLO model.
        
        Args:
            model_path (Path): Path to the YOLO model file
            target_height (int): Target height for frame resizing
        """
        self.logger = logging.getLogger(__name__)

        try:
            self.model = YOLO(str(model_path))
            self.target_height = target_height
            self.names = self.model.model.names
            self.logger.info("Fire detector initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize fire detector: {e}")
            raise

    def resize_frame(self, frame):
        """Resize frame maintaining aspect ratio."""
        height, width = frame.shape[:2]
        aspect_ratio = width / height
        new_width = int(self.target_height * aspect_ratio)
        return cv2.resize(frame, (new_width, self.target_height))

    def process_frame(self, frame):
        """
        Process a video frame to detect fire and smoke.
        
        Returns:
            tuple: (processed_frame, detection: str)
        """
        try:
            frame = self.resize_frame(frame)
            results = self.model(frame)
            detection = None

            if results and len(results[0].boxes) > 0:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
                confidences = results[0].boxes.conf.cpu().numpy()

                for box, class_id, confidence in zip(boxes, class_ids, confidences):
                    class_name = self.names[class_id]
                    x1, y1, x2, y2 = box

                    # Define color for different classes
                    if "fire" == class_name.lower():
                        color = (0, 0, 255)  # Red for fire
                        detection = "Fire"
                    elif "smoke" == class_name.lower():
                        color = (255, 255, 255)  # white for smoke
                        detection = "Smoke"

                    # Draw bounding box and label
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cvzone.putTextRect(
                        frame,
                        f"{class_name}: {confidence:.2f}",
                        (x1, y1),
                        scale=2,
                        thickness=1,
                        colorR=color,
                        colorT=(255, 255, 255) if detection=="Fire" else (0, 0, 0),
                        offset=5,
                    )

            return frame, detection

        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            return frame, None
