from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'IELTS — testlar va videolar'

    def ready(self):
        # Admin paket (modullashtirilgan) — barcha test/savol turlari registratsiyasi
        import core.admin  # noqa: F401
