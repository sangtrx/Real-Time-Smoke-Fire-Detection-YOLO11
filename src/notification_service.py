from twilio.rest import Client
import requests
import cv2
import time
import logging
from pathlib import Path
from datetime import datetime


class NotificationService:
    def __init__(self, config):
        """
        Initialize notification service with configuration.

        Args:
            config: Configuration object containing required credentials
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.twilio_client = Client(
            config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

    def upload_image_to_imgur(self, image_path: Path) -> str:
        """Upload image to Imgur and return the URL."""
        url = 'https://api.imgur.com/3/upload'
        headers = {'Authorization': f'Client-ID {self.config.IMGUR_CLIENT_ID}'}

        try:
            with open(image_path, 'rb') as image_file:
                response = requests.post(
                    url,
                    headers=headers,
                    files={'image': image_file}
                )

                if response.status_code in [200, 201]:
                    image_url = response.json()['data']['link']
                    self.logger.info(
                        f"Image uploaded successfully: {image_url}")
                    return image_url

                self.logger.error(f"Imgur upload failed: {
                                  response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to upload image: {e}")
            return None

    def save_frame(self, frame) -> Path:
        """Save frame to disk and return the path."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = self.config.DETECTED_FIRES_DIR / \
            f'fire_detected_{timestamp}.jpg'
        cv2.imwrite(str(filename), frame)
        return filename

    def send_whatsapp_alert(self, frame, max_retries=3, delay=5):
        """
        Send WhatsApp alert with the detected fire image.

        Args:
            frame: The frame containing the detected fire
            max_retries: Number of retry attempts
            delay: Delay between retries in seconds
        """
        try:
            # Save the frame
            image_path = self.save_frame(frame)
            self.logger.info(f"Frame saved: {image_path}")

            # Upload to Imgur
            img_url = self.upload_image_to_imgur(image_path)
            if not img_url:
                return False

            # Send WhatsApp message
            for attempt in range(max_retries):
                try:
                    message = self.twilio_client.messages.create(
                        body=f'🚨 ALERT: Fire detected! View image here: {
                            img_url}',
                        # media_url=[img_url], # requried upgrading from trial account
                        from_=self.config.TWILIO_WHATSAPP_NUMBER,
                        to=self.config.RECEIVER_WHATSAPP_NUMBER
                    )
                    self.logger.info(
                        f"Alert sent successfully. SID: {message.sid}")
                    return True
                except Exception as e:
                    self.logger.error(
                        f"Alert attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)

            return False

        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
            return False

    def send_test_message(self):
        """Send a test message to verify connectivity."""
        try:
            message = self.twilio_client.messages.create(
                body='🔧 Test: Fire Detection System is operational.',
                from_=self.config.TWILIO_WHATSAPP_NUMBER,
                to=self.config.RECEIVER_WHATSAPP_NUMBER
            )
            self.logger.info("Test message sent successfully")
            return True
        except Exception as e:
            self.logger.error(f"Test message failed: {e}")
            return False
