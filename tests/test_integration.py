import pytest
import cv2
from src.fire_detector import FireDetector
from src.notification_service import NotificationService


def test_full_detection_flow(fire_detector, notification_service, sample_frame):
    """Test complete detection and notification flow"""
    # Process frame
    processed_frame, fire_detected = fire_detector.process_frame(sample_frame)

    # If fire detected, test notification
    if fire_detected:
        result = notification_service.send_whatsapp_alert(processed_frame)
        assert result is True
