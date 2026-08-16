from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from .models import AdminAnnouncement, SATResourceProgress, StudyStreak, UserTestResult
from .services.ai_language import get_ai_language
from .i18n_js import js_catalog


def static_asset_version(request):
    return {'STATIC_ASSET_VERSION': getattr(settings, 'STATIC_ASSET_VERSION', '1')}


def _relative_time(dt):
    if not dt:
        return _("Hozir")
    delta = timezone.now() - dt
    seconds = max(1, int(delta.total_seconds()))
    if seconds < 60:
        return _("Hozirgina")
    minutes = seconds // 60
    if minutes < 60:
        return ngettext("%(n)d daqiqa oldin", "%(n)d daqiqa oldin", minutes) % {'n': minutes}
    hours = minutes // 60
    if hours < 24:
        return ngettext("%(n)d soat oldin", "%(n)d soat oldin", hours) % {'n': hours}
    days = hours // 24
    return ngettext("%(n)d kun oldin", "%(n)d kun oldin", days) % {'n': days}


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
            'title': _("Streakni yo'qotmang"),
            'message': _("Sizda %(n)d kunlik streak bor. Bugun ham o'qishni davom ettiring.") % {'n': current_streak},
            'url': reverse('core:dashboard'),
            'created_at': timezone.now(),
        })

    paused_test = UserTestResult.objects.filter(user=user, is_paused=True).order_by('-paused_at').first()
    if paused_test:
        items.append({
            'kind': 'continue',
            'icon': 'fa-circle-play',
            'title': _("IELTS davom ettirish"),
            'message': _("%(title)s testi to'xtatilgan. Davom ettirishga qayting.") % {'title': paused_test.test.title},
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
            'title': _("SAT davom ettirish"),
            'message': _("%(title)s resursini tugatib qo'ying.") % {'title': sat_progress.resource.title},
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


def site_language(request):
    lang = getattr(request, 'LANGUAGE_CODE', None) or get_ai_language(request)
    return {
        'site_lang': lang,
        'ai_lang': lang,
        'i18n_js': js_catalog(),
    }
