import mimetypes

from django.http import FileResponse, Http404, HttpResponse


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


def stream_protected_media(request, file_field):
    """Login-required media stream with HTTP Range support (video seeking)."""
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
        file_field.open('rb')
        try:
            file_field.seek(start)
            data = file_field.read(length)
        finally:
            file_field.close()

        response = HttpResponse(data, status=206, content_type=content_type)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Content-Length'] = str(length)
    else:
        file_field.open('rb')
        response = FileResponse(file_field, content_type=content_type)
        response['Content-Length'] = str(file_size)

    response['Accept-Ranges'] = 'bytes'
    response['Content-Disposition'] = 'inline'
    response['Cache-Control'] = 'private, no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
