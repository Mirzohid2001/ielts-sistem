from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserOTP


@receiver(post_save, sender=User)
def create_otp_for_new_user(sender, instance, created, **kwargs):
    """Yangi foydalanuvchi yaratilganda avtomatik OTP yaratish"""
    if created:
        UserOTP.create_otp_for_user(instance)

