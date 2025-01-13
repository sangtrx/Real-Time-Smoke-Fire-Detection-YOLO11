import pytest
import cv2
from src.notification_service import NotificationService
from pathlib import Path


def test_notification_service_init(notification_service):
    """Test NotificationService initialization"""
    assert notification_service.twilio_client is not None


def test_save_frame(notification_service, sample_frame):
    """Test frame saving functionality"""
    path = notification_service.save_frame(sample_frame)
    assert path.exists()
    path.unlink()  # Cleanup


def test_imgur_upload(notification_service, sample_frame):
    """Test Imgur upload functionality"""
    # Save temporary image
    path = notification_service.save_frame(sample_frame)
    url = notification_service.upload_image_to_imgur(path)
    assert url is not None and url.startswith('http')
    path.unlink()  # Cleanup


def test_whatsapp_alert(notification_service, sample_frame):
    """Test WhatsApp alert sending"""
    result = notification_service.send_whatsapp_alert(sample_frame)
    assert result is True
