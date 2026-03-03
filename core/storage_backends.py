from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class ContaboPublicStorage(S3Boto3Storage):
    def url(self, name):
        return f"{settings.MEDIA_URL}{name}"