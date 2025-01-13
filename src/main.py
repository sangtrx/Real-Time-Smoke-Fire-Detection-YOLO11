import cv2
import logging
import sys
from pathlib import Path
from config import Config, setup_logging
from fire_detector import FireDetector
from notification_service import NotificationService


def main():
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Fire Detection System")

    try:
        # Validate configuration
        Config.validate()

        # Initialize services
        notification_service = NotificationService(Config)
        if not notification_service.send_test_message():
            logger.error("Failed to send test message. Exiting...")
            sys.exit(1)

        detector = FireDetector(Config.MODEL_PATH)

        # Open video capture
        cap = cv2.VideoCapture('data/vid.mp4')
        if not cap.isOpened():
            logger.error("Failed to open video source")
            sys.exit(1)

        fire_alert_sent = False
        logger.info("Starting video processing")

        while True:
            ret, frame = cap.read()
            if not ret:
                logger.info("Video processing complete")
                break

            # Process frame
            processed_frame, fire_detected = detector.process_frame(frame)

            # Handle fire detection
            if fire_detected and not fire_alert_sent:
                logger.info("Fire detected! Sending alert...")
                if notification_service.send_whatsapp_alert(processed_frame):
                    fire_alert_sent = True

            # Display frame
            cv2.imshow("Fire Detection", processed_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                logger.info("Application terminated by user")
                break

    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    main()
