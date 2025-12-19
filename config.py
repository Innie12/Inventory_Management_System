import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # Security
    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f"sqlite:///{BASE_DIR / 'data.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = str(BASE_DIR / 'exports')
    REPORTS_FOLDER = str(BASE_DIR / 'exports' / 'reports')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Pagination
    ITEMS_PER_PAGE = 12

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # SMS/OTP (Twilio) - Get from https://www.twilio.com/
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
    OTP_EXPIRY_MINUTES = 10

    # Email (Optional - for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER', 'noreply@inventory.com')

    # Currency
    DEFAULT_CURRENCY = 'PHP'
    SUPPORTED_CURRENCIES = ['PHP', 'USD', 'EUR', 'JPY']

    # Notifications
    LOW_STOCK_THRESHOLD = 10
    ENABLE_EMAIL_NOTIFICATIONS = False
    ENABLE_SMS_NOTIFICATIONS = False

    # Reports
    REPORT_LOGO_PATH = str(BASE_DIR / 'static' / 'images' / 'logo.png')
    COMPANY_NAME = 'Your Company Name'
    COMPANY_ADDRESS = 'Your Company Address'
    COMPANY_PHONE = '+63 XXX XXX XXXX'

    # Features
    ENABLE_BARCODE = True
    ENABLE_MULTI_CURRENCY = True
    ENABLE_AUDIT_LOG = True
