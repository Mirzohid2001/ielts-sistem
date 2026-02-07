from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import secrets
import string


class UserOTP(models.Model):
    """Bir martalik parol (OTP) modeli"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=20, unique=True, db_index=True)
    is_used = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "OTP Kod"
        verbose_name_plural = "OTP Kodlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['otp_code', 'is_used']),
            models.Index(fields=['user', 'is_used']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.otp_code}"

    def save(self, *args, **kwargs):
        """Save metodini override qilish - avtomatik to'ldirish"""
        # Agar OTP kod bo'sh bo'lsa, generatsiya qilish
        if not self.otp_code:
            self.otp_code = self.generate_otp()
            # Takrorlanmasligini ta'minlash
            while UserOTP.objects.filter(otp_code=self.otp_code).exclude(pk=self.pk).exists():
                self.otp_code = self.generate_otp()
        
        # Agar expires_at bo'sh bo'lsa, avtomatik to'ldirish
        if not self.expires_at:
            from django.conf import settings
            expiry_hours = getattr(settings, 'OTP_EXPIRY_HOURS', 24)
            self.expires_at = timezone.now() + timedelta(hours=expiry_hours)
        
        super().save(*args, **kwargs)

    def is_valid(self):
        """OTP hali ishlatilmagan va muddati o'tmaganmi tekshirish"""
        if not self.expires_at:
            return False
        return not self.is_used and self.expires_at > timezone.now()

    def mark_as_used(self):
        """OTP ni ishlatilgan deb belgilash"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()

    @staticmethod
    def generate_otp(length=10):
        """OTP kod generatsiya qilish"""
        alphabet = string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def create_otp_for_user(user, expiry_hours=24):
        """Foydalanuvchi uchun yangi OTP yaratish"""
        otp_code = UserOTP.generate_otp()
        # Takrorlanmasligini ta'minlash
        while UserOTP.objects.filter(otp_code=otp_code).exists():
            otp_code = UserOTP.generate_otp()
        
        expires_at = timezone.now() + timedelta(hours=expiry_hours)
        otp = UserOTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expires_at
        )
        return otp
