from io import BytesIO
from tempfile import mkdtemp
from unittest.mock import MagicMock

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.media_streaming import (
    get_direct_media_url,
    serve_protected_media,
    stream_protected_media,
)


class RemoteStorageRedirectTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.remote_field = MagicMock()
        self.remote_field.name = 'videos/lesson.mp4'
        self.remote_field.url = 'https://cdn.example/ielts/videos/lesson.mp4'
        self.remote_field.storage = MagicMock()
        self.remote_field.storage.bucket_name = 'ielts'
        self.remote_field.storage.connection.meta.client.generate_presigned_url.return_value = (
            'https://cdn.example/signed/videos/lesson.mp4?sig=abc'
        )

    @override_settings(VIDEO_STREAM_DIRECT=True, VIDEO_USE_PRESIGNED_URLS=True)
    def test_remote_storage_redirects_with_presigned_url(self):
        request = self.factory.get('/videos/1/stream/')
        response = serve_protected_media(request, self.remote_field)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response['Location'], 'https://cdn.example/signed/videos/lesson.mp4?sig=abc')

    @override_settings(VIDEO_STREAM_DIRECT=True, VIDEO_USE_PRESIGNED_URLS=False)
    def test_remote_storage_redirects_to_public_url_when_presign_disabled(self):
        request = self.factory.get('/videos/1/stream/')
        response = serve_protected_media(request, self.remote_field)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response['Location'], 'https://cdn.example/ielts/videos/lesson.mp4')


class LocalStorageStreamTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.storage = FileSystemStorage(location=mkdtemp())
        self.name = self.storage.save('videos/local.mp4', ContentFile(b'0123456789abcdef'))

    def _field(self):
        storage = self.storage
        name = self.name

        class FakeField:
            def __init__(self):
                self.storage = storage
                self.name = name
                self.size = storage.size(name)
                self.file = None

            def open(self, mode='rb'):
                self.file = storage.open(name, mode)
                return self.file

            def seek(self, pos):
                return self.file.seek(pos)

            def read(self, size=-1):
                return self.file.read(size)

            def close(self):
                if self.file:
                    self.file.close()

        return FakeField()

    @override_settings(VIDEO_STREAM_DIRECT=True)
    def test_local_storage_streams_without_redirect(self):
        request = self.factory.get('/videos/1/stream/')
        response = serve_protected_media(request, self._field())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'0123456789abcdef')

    def test_range_request_returns_partial_content(self):
        request = self.factory.get('/videos/1/stream/', HTTP_RANGE='bytes=2-5')
        response = stream_protected_media(request, self._field())
        self.assertEqual(response.status_code, 206)
        self.assertEqual(b''.join(response.streaming_content), b'2345')
        self.assertEqual(response['Content-Range'], 'bytes 2-5/16')


class GetDirectMediaUrlTests(SimpleTestCase):
    @override_settings(VIDEO_USE_PRESIGNED_URLS=True, VIDEO_PRESIGNED_URL_EXPIRY=3600)
    def test_presign_failure_falls_back_to_public_url(self):
        field = MagicMock()
        field.name = 'videos/x.mp4'
        field.url = 'https://cdn.example/x.mp4'
        field.storage.connection.meta.client.generate_presigned_url.side_effect = Exception('no creds')
        self.assertEqual(get_direct_media_url(field), 'https://cdn.example/x.mp4')
