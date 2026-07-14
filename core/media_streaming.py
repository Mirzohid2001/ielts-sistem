import mimetypes

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse


def _guess_content_type(filename):
    content_type, _ = mimetypes.guess_type(filename)
    if content_type:
        return content_type
    lower = (filename or '').lower()
    if lower.endswith('.mp4'):
        return 'video/mp4'
    if lower.endswith('.webm'):
        return 'video/webm'
    if lower.endswith('.ogg') or lower.endswith('.ogv'):
        return 'video/ogg'
    return 'application/octet-stream'


def _is_remote_storage(file_field):
    storage = file_field.storage
    if isinstance(storage, FileSystemStorage):
        return False
    return hasattr(storage, 'bucket_name') or hasattr(storage, 'connection')


def get_direct_media_url(file_field):
    """
    Direct Contabo/S3 URL for the browser — same style as Django admin file link.

    Default: public object URL (fast, cacheable). Optional: short-lived signed URL
    when VIDEO_USE_PRESIGNED_URLS=1 (private buckets).
    """
    use_presigned = getattr(settings, 'VIDEO_USE_PRESIGNED_URLS', False)
    storage = file_field.storage

    if use_presigned and hasattr(storage, 'connection'):
        try:
            client = storage.connection.meta.client
            bucket = storage.bucket_name
            expire_seconds = getattr(settings, 'VIDEO_PRESIGNED_URL_EXPIRY', 7200)
            return client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': file_field.name},
                ExpiresIn=expire_seconds,
            )
        except Exception:
            pass

    return file_field.url


def serve_protected_media(request, file_field):
    """
    Login-required media access.

    Remote storage (S3): redirect so the browser streams directly from the bucket
    with native Range support — avoids proxying gigabytes through Gunicorn.
    Local storage: stream through Django with HTTP Range support.
    """
    if not file_field:
        raise Http404

    if getattr(settings, 'VIDEO_STREAM_DIRECT', True) and _is_remote_storage(file_field):
        url = get_direct_media_url(file_field)
        response = HttpResponse(status=307)
        response['Location'] = url
        response['Cache-Control'] = 'private, no-store'
        return response

    return stream_protected_media(request, file_field)


def _range_iterator(file_field, start, length, chunk_size=256 * 1024):
    file_field.open('rb')
    try:
        file_field.seek(start)
        remaining = length
        while remaining > 0:
            data = file_field.read(min(chunk_size, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data
    finally:
        file_field.close()


def stream_protected_media(request, file_field):
    """Local/fallback media stream with HTTP Range support (video seeking)."""
    if not file_field:
        raise Http404

    file_size = file_field.size
    content_type = _guess_content_type(file_field.name)
    range_header = request.META.get('HTTP_RANGE', '').strip()

    if range_header.startswith('bytes='):
        try:
            byte_range = range_header.replace('bytes=', '', 1).split('-', 1)
            start = int(byte_range[0]) if byte_range[0] else 0
            end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
        except (ValueError, IndexError):
            start, end = 0, file_size - 1
        start = max(0, start)
        end = min(end, file_size - 1)
        if start > end or start >= file_size:
            response = HttpResponse(status=416)
            response['Content-Range'] = f'bytes */{file_size}'
            return response

        length = end - start + 1
        response = StreamingHttpResponse(
            _range_iterator(file_field, start, length),
            status=206,
            content_type=content_type,
        )
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Content-Length'] = str(length)
    else:
        file_handle = file_field.open('rb')
        response = FileResponse(file_handle, content_type=content_type)
        response['Content-Length'] = str(file_size)

    response['Accept-Ranges'] = 'bytes'
    response['Content-Disposition'] = 'inline'
    response['Cache-Control'] = 'private, no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
