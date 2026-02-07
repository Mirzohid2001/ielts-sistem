"""
YouTube URL utilities for Django templates
"""
import re
from django import template

register = template.Library()


@register.filter
def youtube_id(url):
    """
    Extract YouTube video ID from any YouTube URL format.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    - URLs with extra params: &t=, &list=, &si=, etc.
    - Direct video ID (11 characters)
    
    Usage: {{ video.youtube_url|youtube_id }}
    """
    if not url:
        return ''
    
    url = str(url).strip()
    
    # If it's already a valid 11-character video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    
    # Patterns to extract video ID from various YouTube URL formats
    patterns = [
        # Standard watch URL: https://www.youtube.com/watch?v=VIDEO_ID
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        # Short URL: https://youtu.be/VIDEO_ID
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        # Embed URL: https://www.youtube.com/embed/VIDEO_ID
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        # Shorts URL: https://www.youtube.com/shorts/VIDEO_ID
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        # Old format: https://www.youtube.com/v/VIDEO_ID
        r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
        # Mobile: https://m.youtube.com/watch?v=VIDEO_ID
        r'(?:m\.youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        # URL with params: watch?.*v=VIDEO_ID
        r'[?&]v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            video_id = match.group(1)
            # Validate video ID length (must be exactly 11 characters)
            if video_id and len(video_id) == 11:
                return video_id
    
    return ''


@register.filter
def youtube_embed_url(url, use_nocookie=True):
    """
    Convert YouTube URL to embed URL.
    
    Usage: {{ video.youtube_url|youtube_embed_url }}
    Usage with nocookie: {{ video.youtube_url|youtube_embed_url:True }}
    """
    video_id = youtube_id(url)
    if not video_id:
        return ''
    
    if use_nocookie:
        return f'https://www.youtube-nocookie.com/embed/{video_id}'
    return f'https://www.youtube.com/embed/{video_id}'

