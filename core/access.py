from core.models import UserModuleAccess


def get_user_module_access(user):
    """Har bir user uchun access yozuvini kafolatlash."""
    access, _ = UserModuleAccess.objects.get_or_create(user=user)
    return access
