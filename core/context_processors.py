from django.urls import reverse
from django.utils import timezone

from .models import AdminAnnouncement, SATResourceProgress, StudyStreak, UserTestResult


def _relative_time(dt):
    if not dt:
        return "Hozir"
    delta = timezone.now() - dt
    seconds = max(1, int(delta.total_seconds()))
    if seconds < 60:
        return "Hozirgina"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} daqiqa oldin"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} soat oldin"
    days = hours // 24
    return f"{days} kun oldin"


def build_notification_items(user, limit=8):
    today = timezone.localdate()
    items = []

    current_streak = StudyStreak.get_current_streak(user)
    studied_today = StudyStreak.objects.filter(
        user=user,
        date=today,
        activities_count__gt=0,
    ).exists()
    if current_streak > 0 and not studied_today:
        items.append({
            'kind': 'streak',
            'icon': 'fa-fire',
            'title': "Streakni yo'qotmang",
            'message': f"Sizda {current_streak} kunlik streak bor. Bugun ham o'qishni davom ettiring.",
            'url': reverse('core:dashboard'),
            'created_at': timezone.now(),
        })

    paused_test = UserTestResult.objects.filter(user=user, is_paused=True).order_by('-paused_at').first()
    if paused_test:
        items.append({
            'kind': 'continue',
            'icon': 'fa-circle-play',
            'title': "IELTS davom ettirish",
            'message': f"{paused_test.test.title} testi to'xtatilgan. Davom ettirishga qayting.",
            'url': reverse('core:test_resume', kwargs={'pk': paused_test.id}),
            'created_at': paused_test.paused_at or paused_test.started_at,
        })

    sat_progress = SATResourceProgress.objects.filter(
        user=user,
        watch_percentage__gt=0,
        watch_percentage__lt=90,
    ).select_related('resource').order_by('-last_accessed_at').first()
    if sat_progress:
        items.append({
            'kind': 'continue',
            'icon': 'fa-book-open-reader',
            'title': "SAT davom ettirish",
            'message': f"{sat_progress.resource.title} resursini tugatib qo'ying.",
            'url': reverse('sat:sat_subject', kwargs={'subject': sat_progress.resource.subject}),
            'created_at': sat_progress.last_accessed_at,
        })

    now = timezone.now()
    announcement_qs = AdminAnnouncement.objects.filter(is_active=True).order_by('-created_at')
    for ann in announcement_qs[:5]:
        if ann.starts_at and ann.starts_at > now:
            continue
        if ann.ends_at and ann.ends_at < now:
            continue
        items.append({
            'kind': 'announcement',
            'icon': 'fa-bullhorn',
            'title': ann.title,
            'message': ann.message,
            'url': ann.link_url,
            'created_at': ann.created_at,
        })

    for item in items:
        item['time_ago'] = _relative_time(item.get('created_at'))

    items = sorted(items, key=lambda x: x.get('created_at') or timezone.now(), reverse=True)
    return items[:limit]


def platform_notifications(request):
    if not request.user.is_authenticated:
        return {'notification_items': [], 'notification_count': 0}

    items = build_notification_items(request.user, limit=8)
    return {
        'notification_items': items,
        'notification_count': len(items),
    }
