from twilio.rest import Client
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """SMS service for sending OTP and notifications"""

    def __init__(self):
        self.client = None
        self.from_number = None
        self._init_client()

    def _init_client(self):
        """Initialize Twilio client"""
        try:
            account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
            auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
            self.from_number = current_app.config.get('TWILIO_PHONE_NUMBER')

            if account_sid and auth_token and self.from_number:
                self.client = Client(account_sid, auth_token)
                logger.info("Twilio client initialized successfully")
            else:
                logger.warning("Twilio credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {str(e)}")

    def send_otp(self, phone_number, otp_code):
        """Send OTP code to phone number"""
        if not self.client:
            logger.warning(
                f"SMS not configured. OTP for {phone_number}: {otp_code}")
            return {'success': False, 'error': 'SMS service not configured'}

        try:
            message_body = f"Your verification code is: {otp_code}\nValid for 10 minutes.\n\n- Inventory System"

            message = self.client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=phone_number
            )

            logger.info(f"OTP sent to {phone_number}. SID: {message.sid}")
            return {'success': True, 'sid': message.sid}

        except Exception as e:
            logger.error(f"Failed to send OTP to {phone_number}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_notification(self, phone_number, message):
        """Send notification SMS"""
        if not self.client:
            logger.warning(
                f"SMS not configured. Message for {phone_number}: {message}")
            return {'success': False, 'error': 'SMS service not configured'}

        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone_number
            )

            logger.info(f"Notification sent to {phone_number}. SID: {msg.sid}")
            return {'success': True, 'sid': msg.sid}

        except Exception as e:
            logger.error(
                f"Failed to send notification to {phone_number}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_low_stock_alert(self, phone_number, product_name, quantity):
        """Send low stock alert"""
        message = f"LOW STOCK ALERT!\n\nProduct: {product_name}\nCurrent Stock: {quantity}\n\nPlease reorder soon."
        return self.send_notification(phone_number, message)


# Fallback mock service for development without Twilio
class MockSMSService:
    """Mock SMS service for testing"""

    def send_otp(self, phone_number, otp_code):
        print(f"\n{'='*50}")
        print(f"MOCK SMS TO: {phone_number}")
        print(f"OTP CODE: {otp_code}")
        print(f"{'='*50}\n")
        return {'success': True, 'mock': True}

    def send_notification(self, phone_number, message):
        print(f"\n{'='*50}")
        print(f"MOCK SMS TO: {phone_number}")
        print(f"MESSAGE: {message}")
        print(f"{'='*50}\n")
        return {'success': True, 'mock': True}

    def send_low_stock_alert(self, phone_number, product_name, quantity):
        return self.send_notification(
            phone_number,
            f"LOW STOCK: {product_name} - Qty: {quantity}"
        )


def get_sms_service():
    """Get SMS service instance (real or mock)"""
    try:
        return SMSService()
    except:
        return MockSMSService()
