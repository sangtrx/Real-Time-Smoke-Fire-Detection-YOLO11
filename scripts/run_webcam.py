import cv2
import logging
import sys
import time
from pathlib import Path

from src.config import Config, setup_logging
from src.fire_detector import Detector
from src.notification_service import NotificationService


def run_webcam(max_frames: int = None, conf: float = 0.5):
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting webcam demo")

    notification_service = NotificationService(Config)
    detector = Detector(Config.MODEL_PATH, iou_threshold=0.20, min_confidence=conf)

    # Try to open default webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.warning("Webcam /dev/video0 not available, falling back to sample video")
        cap = cv2.VideoCapture(str(Config.VIDEO_SOURCE))
        if not cap.isOpened():
            logger.error(f"Failed to open webcam and fallback video {Config.VIDEO_SOURCE}")
            sys.exit(1)
        else:
            logger.info(f"Opened fallback video: {Config.VIDEO_SOURCE}")
    else:
        logger.info("Opened webcam /dev/video0")

    last_alert_time = 0
    alert_cooldown = Config.ALERT_COOLDOWN

    frame_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.info("Video input ended")
                break

            processed_frame, detection = detector.process_frame(frame)

            # Alert logic (non-blocking)
            if detection:
                current_time = time.time()
                if (current_time - last_alert_time) > alert_cooldown:
                    logger.warning(f"{detection} detected — sending alert")
                    # send alert asynchronously if desired
                    try:
                        notification_service.send_alert(processed_frame, detection)
                    except Exception as e:
                        logger.error(f"Failed to send alert: {e}")
                    last_alert_time = current_time

            # Show frame
            cv2.imshow("Fire Detection (Press q to quit)", processed_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                logger.info("User requested exit")
                break

            frame_count += 1
            if max_frames and frame_count >= max_frames:
                logger.info(f"Reached max frames: {max_frames}")
                break

    except Exception as e:
        logger.critical(f"Runtime error in webcam demo: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Webcam demo stopped")


if __name__ == '__main__':
    # Optional CLI simple arg parsing
    import argparse
    parser = argparse.ArgumentParser(description='Run webcam demo (UI).')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='Stop after this many frames (for testing)')
    parser.add_argument('--conf', type=float, default=0.5,
                        help='Minimum confidence threshold for detections (0-1)')
    args = parser.parse_args()
    run_webcam(max_frames=args.max_frames, conf=args.conf)
