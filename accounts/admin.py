from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from .models import UserOTP
from .utils import generate_otp_for_user


class UserOTPInline(admin.TabularInline):
    """User admin da OTP kodlarni ko'rsatish"""
    model = UserOTP
    extra = 0
    readonly_fields = ['otp_code', 'is_used', 'is_valid_display', 'created_at', 'expires_at', 'used_at']
    can_delete = False
    fields = ['otp_code', 'is_used', 'is_valid_display', 'created_at', 'expires_at']
    exclude = []  # Barcha fieldlar ko'rsatiladi, lekin readonly
    
    def has_add_permission(self, request, obj=None):
        """Inline formda qo'shishni o'chirish - faqat signal orqali yaratiladi"""
        return False
    
    def is_valid_display(self, obj):
        if not obj or not obj.pk:
            return format_html('<span style="color: gray;">-</span>')
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Ha</span>')
        return format_html('<span style="color: red;">✗ Yo\'q</span>')
    is_valid_display.short_description = "Yaroqli"


@admin.register(UserOTP)
class UserOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp_code', 'is_used', 'is_valid', 'created_at', 'expires_at', 'used_at']
    list_filter = ['is_used', 'created_at', 'expires_at']
    search_fields = ['user__username', 'user__email', 'otp_code']
    readonly_fields = ['otp_code', 'created_at', 'expires_at', 'used_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('user', 'otp_code', 'is_used')
        }),
        ('Vaqt', {
            'fields': ('created_at', 'expires_at', 'used_at')
        }),
    )

    def is_valid(self, obj):
        if not obj or not obj.pk:
            return format_html('<span style="color: gray;">-</span>')
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Ha</span>')
        return format_html('<span style="color: red;">✗ Yo\'q</span>')
    is_valid.short_description = "Yaroqli"


# User admin ni extend qilish
class UserAdmin(BaseUserAdmin):
    inlines = [UserOTPInline]
    actions = ['generate_otp_action']
    
    def generate_otp_action(self, request, queryset):
        """Foydalanuvchilar uchun OTP yaratish"""
        count = 0
        for user in queryset:
            otp = generate_otp_for_user(user)
            count += 1
        self.message_user(request, f"{count} ta foydalanuvchi uchun OTP yaratildi.")
    generate_otp_action.short_description = "OTP kod yaratish"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            return actions
        return actions


# Mavjud UserAdmin ni almashtirish
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
