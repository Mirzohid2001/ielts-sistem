from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import UserOTP


def generate_otp_for_user(user, expiry_hours=None):
    """Foydalanuvchi uchun OTP yaratish"""
    if expiry_hours is None:
        expiry_hours = getattr(settings, 'OTP_EXPIRY_HOURS', 24)
    
    return UserOTP.create_otp_for_user(user, expiry_hours)

