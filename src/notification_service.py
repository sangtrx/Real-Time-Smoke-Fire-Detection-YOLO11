# notification_service.py
from cryptography.fernet import Fernet
import json
import os
import requests
import cv2
import time
import logging
import asyncio
import telegram
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Setup environment and logging
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv()
logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, config):
        """Initialize notification services"""
        self.config = config
        self.loop = asyncio.new_event_loop()
        self._init_services()

    def _init_services(self):
        """Initialize and validate notification providers"""
        # WhatsApp initialization
        if all([os.getenv("CALLMEBOT_API_KEY"), os.getenv("RECEIVER_WHATSAPP_NUMBER")]):
            self.whatsapp_enabled = True
            self.base_url = "https://api.callmebot.com/whatsapp.php"
            logger.info("WhatsApp service initialized")
        else:
            logger.warning("WhatsApp alerts disabled: Missing credentials")

        # Telegram initialization
        if token := os.getenv("TELEGRAM_TOKEN"):
            try:
                self.telegram_bot = FlareGuardBot(
                    token, os.getenv("TELEGRAM_CHAT_ID"))
                # Run all async initialization together
                self.loop.run_until_complete(self._init_telegram())
            except Exception as e:
                logger.error(f"Telegram setup failed: {e}")
                self.telegram_bot = None
        else:
            logger.info("Telegram alerts disabled: Missing token")

    async def _init_telegram(self):
        """Async initialization for Telegram"""
        await self.telegram_bot.initialize()
        logger.info("Telegram service initialized")

    def save_frame(self, frame) -> Path:
        """Save detection frame with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        filename = self.config.DETECTED_FIRES_DIR / f'alert_{timestamp}.jpg'
        cv2.imwrite(str(filename), frame)
        return filename

    def upload_image(self, image_path: Path) -> str:
        """Upload image to Imgur CDN"""
        try:
            response = requests.post(
                'https://api.imgur.com/3/upload',
                headers={
                    'Authorization': f'Client-ID {self.config.IMGUR_CLIENT_ID}'},
                files={'image': image_path.open('rb')},
                timeout=10
            )
            response.raise_for_status()
            return response.json()['data']['link']
        except Exception as e:
            logger.error(f"Image upload failed: {str(e)}")
            return None

    def send_alert(self, frame, detection: str = "Fire") -> bool:
        """Main alert dispatch method"""
        image_path = self.save_frame(frame)
        success = False
        # Send WhatsApp alert if enabled
        if self.whatsapp_enabled:
            success = self._send_whatsapp_alert(image_path, detection)
        # Send Telegram alert if enabled
        if self.telegram_bot:
            success |= self._send_telegram_alert(image_path, detection)
        return success

    def _send_whatsapp_alert(self, image_path, detection):
        """Handle WhatsApp notification flow"""
        image_url = self.upload_image(image_path)
        if not image_url:
            logger.error("WhatsApp alert skipped: Image upload failed")
            return False

        message = f"🚨 {detection} Detected! View at {image_url}"
        encoded_msg = quote_plus(message)
        url = f"{self.base_url}?" \
            f"phone={os.getenv('RECEIVER_WHATSAPP_NUMBER')}&" \
            f"text={encoded_msg}&" \
            f"apikey={os.getenv('CALLMEBOT_API_KEY')}"

        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            logger.info("WhatsApp alert delivered")
            return True
        logger.warning(
            f"WhatsApp Alert Attempt failed: HTTP {response.status_code}")

        return False

    def _send_telegram_alert(self, image_path, detection):
        """Handle Telegram notification with loop reuse"""
        try:
            return self.loop.run_until_complete(
                self.telegram_bot.send_alert(
                    image_path=image_path,
                    caption=f"🚨 {detection} Detected!"
                )
            )
        except Exception as e:
            logger.error(f"Telegram alert failed: {str(e)}")
            return False

    def send_test_message(self):
        """Verify system connectivity"""
        success = False
        if self.whatsapp_enabled:
            test_msg = "🔧 System Test: Fire Detection System Operational"
            success = self._send_callmebot_message(test_msg)
        if self.telegram_bot:
            try:
                test_image = Path(PROJECT_ROOT, 'data', "test_image.png")
                success |= self.loop.run_until_complete(
                    self.telegram_bot.send_test_alert(test_image))
            except Exception as e:
                logger.error(f"Telegram test failed: {e}")
                success = False
        return success

    def _send_callmebot_message(self, message: str) -> bool:
        """Core WhatsApp message sender"""
        encoded_msg = quote_plus(message)
        url = f"{self.base_url}?" \
            f"phone={os.getenv('RECEIVER_WHATSAPP_NUMBER')}&" \
            f"text={encoded_msg}&" \
            f"apikey={os.getenv('CALLMEBOT_API_KEY')}"

        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            logger.info("WhatsApp alert delivered")
            return True
        logger.warning(
            f"WhatsApp Alert Attempt failed: HTTP {response.status_code}")
        return False

    def __del__(self):
        """Cleanup event loop"""
        if hasattr(self, 'loop') and not self.loop.is_closed():
            self.loop.close()


class FlareGuardBot:
    def __init__(self, token: str, default_chat_id: str = None):
        """
        Secure Telegram alert bot with encrypted storage
        Args:
            token: Telegram bot token
            default_chat_id: Optional predefined chat ID
        """
        self.logger = logging.getLogger(__name__)
        self.token = token
        self.default_chat_id = default_chat_id
        self.bot = telegram.Bot(token=self.token)
        # Encryption setup
        self._init_crypto()
        self.storage_file = Path(__file__).parent / "sysdata.bin"
        self.chat_ids = self._load_chat_ids()

    async def initialize(self):
        """Async initialization sequence"""
        await self._update_chat_ids()

    def _init_crypto(self):
        """Initialize encryption system"""
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable required")
        self.cipher_suite = Fernet(key.encode())

    def _load_chat_ids(self):
        """Load encrypted chat IDs from secure storage"""
        try:
            if self.storage_file.exists():
                self.storage_file.chmod(0o600)
                with open(self.storage_file, "rb") as f:
                    encrypted_data = f.read()
                    decrypted = self.cipher_suite.decrypt(encrypted_data)
                    ids = json.loads(decrypted)
                    if not all(isinstance(i, int) for i in ids):
                        raise ValueError("Invalid chat ID format")
                    return ids
            return []
        except Exception as e:
            self.logger.error(f"Failed to load chat IDs: {e}")
            return []

    def _save_chat_ids(self):
        """Securely store chat IDs with encryption"""
        try:
            encrypted = self.cipher_suite.encrypt(
                json.dumps(self.chat_ids).encode()
            )
            with open(self.storage_file, "wb") as f:
                f.write(encrypted)
            self.storage_file.chmod(0o600)
        except Exception as e:
            self.logger.error(f"Failed to save chat IDs: {e}")

    async def _update_chat_ids(self):
        """Discover and store new chat IDs securely"""
        try:
            updates = await self.bot.get_updates()
            new_ids = []
            for update in updates:
                chat_id = update.message.chat_id
                if chat_id not in self.chat_ids:
                    new_ids.append(chat_id)
                    self.chat_ids.append(chat_id)
                    self.logger.info(f"New chat ID registered: {chat_id}")
            if new_ids:
                self._save_chat_ids()
                self.logger.info(f"Saved {len(new_ids)} new chat IDs")
        except Exception as e:
            self.logger.error(f"Chat ID update failed: {e}")

    async def send_alert(self, image_path: Path, caption: str) -> bool:
        """Send alert to all registered chats with retry logic"""
        if not image_path.exists():
            self.logger.error(f"Alert image missing: {image_path}")
            return False

        success = False
        try:
            async with self.bot:
                for chat_id in self.chat_ids:
                    for attempt in range(3):
                        try:
                            with open(image_path, 'rb') as photo:
                                await self.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=photo,
                                    caption=caption,
                                    parse_mode='Markdown',
                                    pool_timeout=20
                                )
                            self.logger.info(
                                f"Alert sent to Telegram chat {chat_id}")
                            success = True
                            break
                        except telegram.error.TimedOut:
                            await asyncio.sleep(2 ** attempt)
                            self.logger.warning(f"Timeout sending to {
                                                chat_id}, retry {attempt+1}/3")
                        except telegram.error.NetworkError:
                            await asyncio.sleep(5)
                            self.logger.warning(f"Network error with {
                                                chat_id}, retry {attempt+1}/3")
                        except Exception as e:
                            self.logger.error(f"Failed to send to {
                                              chat_id}: {str(e)}")
                            break
        except Exception as e:
            self.logger.error(f"Telegram error: {str(e)}")

        return success

    async def send_test_alert(self, test_image: Path):
        """Special method for test alerts"""
        return await self.send_alert(test_image, "🔧 System Test: Service Operational")
