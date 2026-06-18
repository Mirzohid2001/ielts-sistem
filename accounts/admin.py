from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from .models import UserOTP
from .utils import generate_otp_for_user
from core.models import UserModuleAccess


def upsert_user_module_access(user, *, can_access_ielts=True, can_access_sat=True, can_access_jobs=False):
    """Signal allaqachon yaratgan bo'lsa yangilaydi, aks holda yaratadi (INSERT dublikat emas)."""
    access, _ = UserModuleAccess.objects.update_or_create(
        user=user,
        defaults={
            'can_access_ielts': can_access_ielts,
            'can_access_sat': can_access_sat,
            'can_access_jobs': can_access_jobs,
        },
    )
    return access


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


class UserModuleAccessInline(admin.StackedInline):
    """User uchun modul ruxsatlarini oddiy toggle ko'rinishida berish."""
    model = UserModuleAccess
    extra = 0
    max_num = 1
    can_delete = False
    fields = ['can_access_ielts', 'can_access_sat', 'can_access_jobs', 'active_session_key', 'updated_at']
    readonly_fields = ['active_session_key', 'updated_at']

    def get_formset(self, request, obj=None, **kwargs):
        BaseFormSet = super().get_formset(request, obj, **kwargs)

        class UserModuleAccessFormSet(BaseFormSet):
            def _save_access(self, form):
                row = form.save(commit=False)
                user = row.user if getattr(row, 'user_id', None) else self.instance
                return upsert_user_module_access(
                    user,
                    can_access_ielts=row.can_access_ielts,
                    can_access_sat=row.can_access_sat,
                    can_access_jobs=row.can_access_jobs,
                )

            def save_new(self, form, commit=True):
                return self._save_access(form)

            def save_existing(self, form, instance, commit=True):
                return self._save_access(form)

        UserModuleAccessFormSet.__name__ = BaseFormSet.__name__
        return UserModuleAccessFormSet


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
    inlines = [UserModuleAccessInline, UserOTPInline]
    actions = ['generate_otp_action']
    fieldsets = (
        ('Asosiy ma\'lumotlar', {'fields': ('username', 'password')}),
        ('Shaxsiy ma\'lumotlar', {'fields': ('first_name', 'last_name', 'email')}),
        ('Tizim holati', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Muhim sanalar', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )
    
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

    def get_inline_instances(self, request, obj=None):
        if obj:
            UserModuleAccess.objects.get_or_create(user=obj)
        return super().get_inline_instances(request, obj)


# Mavjud UserAdmin ni almashtirish
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
