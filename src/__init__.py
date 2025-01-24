"""
Fire Detection System
A real-time fire detection and notification system using computer vision.
"""

__version__ = '1.0.0'
__author__ = 'Sayed Gamal'
__email__ = 'sayyedgamall@gmail.com'

from .config import Config, setup_logging
from .fire_detector import FireDetector
from .notification_service import NotificationService

__all__ = [
    'Config',
    'setup_logging',
    'FireDetector',
    'NotificationService',
]
