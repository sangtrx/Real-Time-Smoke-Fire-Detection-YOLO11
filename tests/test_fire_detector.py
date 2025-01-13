import pytest
import cv2
import numpy as np
from src.fire_detector import FireDetector


def test_fire_detector_initialization(fire_detector):
    """Test FireDetector initialization"""
    assert fire_detector.model is not None
    assert fire_detector.target_height == 500


def test_resize_frame(fire_detector, sample_frame):
    """Test frame resizing"""
    resized = fire_detector.resize_frame(sample_frame)
    assert resized.shape[0] == 500
    assert resized.shape[2] == 3


def test_process_frame(fire_detector, sample_frame):
    """Test frame processing"""
    processed_frame, fire_detected = fire_detector.process_frame(sample_frame)
    assert isinstance(processed_frame, np.ndarray)
    assert isinstance(fire_detected, bool)
