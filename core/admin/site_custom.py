"""Admin bosh sahifa va index override (CustomAdminSite — kelajakda statistics URL uchun)."""
import json
from datetime import timedelta
from types import MethodType

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Avg, Count, F, Max, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render
from django.urls import path
from django.utils import timezone

from ..models import (
    Category,
    Test,
    UserActivity,
    UserTestResult,
    UserVideoProgress,
    VideoLesson,
)

ACTIVE_USERS_DEFAULT_DAYS = 90
ACTIVE_USERS_MAX_LIMIT = 50
ACTIVE_USERS_PERIOD_CHOICES = (7, 30, 90, 180, 365)


def _gather_active_user_ids(since):
    """Katta JOIN o'rniga alohida indekslangan so'rovlar — tezroq."""
    ids = set(
        User.objects.filter(last_login__gte=since)
        .exclude(username__startswith='demo_')
        .values_list('pk', flat=True)
    )
    ids.update(
        UserTestResult.objects.filter(
            completed_at__isnull=False,
            completed_at__gte=since,
        ).values_list('user_id', flat=True)
    )
    ids.update(
        UserVideoProgress.objects.filter(
            Q(last_watched_at__gte=since) | Q(completed_at__gte=since)
        ).values_list('user_id', flat=True)
    )
    ids.update(
        UserActivity.objects.filter(created_at__gte=since).values_list('user_id', flat=True)
    )
    if not ids:
        return []
    return list(
        User.objects.filter(pk__in=ids)
        .exclude(username__startswith='demo_')
        .values_list('pk', flat=True)
    )


def count_active_users(days):
    return len(_gather_active_user_ids(timezone.now() - timedelta(days=days)))


def parse_active_users_period(request):
    """GET ?period=30 — 7 dan 730 kungacha."""
    raw = request.GET.get('period', ACTIVE_USERS_DEFAULT_DAYS)
    try:
        days = int(raw)
    except (TypeError, ValueError):
        days = ACTIVE_USERS_DEFAULT_DAYS
    return max(7, min(days, 730))


def build_active_users_report(days=ACTIVE_USERS_DEFAULT_DAYS, limit=ACTIVE_USERS_MAX_LIMIT):
    """Faol foydalanuvchilar — faqat kerakli ID lar bo'yicha, LIMIT bilan."""
    since = timezone.now() - timedelta(days=days)
    active_ids = _gather_active_user_ids(since)
    if not active_ids:
        return []

    period_test = Q(test_results__completed_at__gte=since, test_results__completed_at__isnull=False)
    period_video = Q(video_progress__last_watched_at__gte=since) | Q(
        video_progress__completed_at__gte=since
    )
    period_activity = Q(activities__created_at__gte=since)

    users = list(
        User.objects.filter(pk__in=active_ids)
        .annotate(
            tests_period=Count('test_results', filter=period_test, distinct=True),
            videos_period=Count('video_progress', filter=period_video, distinct=True),
            activities_period=Count('activities', filter=period_activity, distinct=True),
            avg_score_period=Avg('test_results__percentage', filter=period_test),
            last_test_at=Max('test_results__completed_at', filter=period_test),
            last_video_at=Max('video_progress__last_watched_at'),
            last_activity_log=Max('activities__created_at'),
        )
        .annotate(
            activity_score=F('tests_period') + F('videos_period') + F('activities_period'),
        )
        .order_by('-activity_score', '-last_login')[:limit]
    )

    for user in users:
        stamps = [user.last_login, user.last_test_at, user.last_video_at, user.last_activity_log]
        user.last_seen = max((d for d in stamps if d), default=None)

    return users


def build_active_users_monthly_trend(days=365):
    """Oxirgi 12 oy — faollik jurnali (yengil so'rov)."""
    since = timezone.now() - timedelta(days=min(days, 365))
    rows = list(
        UserActivity.objects.filter(created_at__gte=since)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('user', distinct=True))
        .order_by('month')[:12]
    )
    labels = []
    counts = []
    for row in rows:
        if row['month']:
            labels.append(row['month'].strftime('%b %Y'))
            counts.append(row['count'])
    return labels, counts


def build_active_users_summary():
    """7/30/90/180/365 — 2 daqiqa kesh (admin index tezligi)."""
    cache_key = 'core:admin_active_users_summary_v2'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = [
        {'days': days, 'count': count_active_users(days)}
        for days in ACTIVE_USERS_PERIOD_CHOICES
    ]
    cache.set(cache_key, data, 120)
    return data


# Custom Admin Site - Statistikalar bilan
class CustomAdminSite(admin.AdminSite):
    site_header = "IELTS Center - Admin Panel"
    site_title = "IELTS Admin"
    index_title = "Boshqaruv paneli"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('statistics/', self.admin_view(self.statistics_view), name='statistics'),
        ]
        return custom_urls + urls
    
    def statistics_view(self, request):
        """Umumiy statistikalar"""
        # Foydalanuvchilar statistikasi
        total_users = User.objects.count()
        active_users_7d = count_active_users(7)
        active_users_30d = count_active_users(30)
        active_users_365d = count_active_users(365)
        
        # Test statistikasi
        total_tests = Test.objects.filter(is_active=True).count()
        total_test_results = UserTestResult.objects.filter(completed_at__isnull=False).count()
        passed_tests = UserTestResult.objects.filter(completed_at__isnull=False).filter(
            percentage__gte=F('test__passing_score')
        ).count()
        failed_tests = total_test_results - passed_tests
        
        # O'rtacha ball
        avg_score = UserTestResult.objects.filter(
            completed_at__isnull=False
        ).aggregate(avg=Avg('percentage'))['avg'] or 0
        
        # Video statistikasi
        total_videos = VideoLesson.objects.filter(is_active=True).count()
        total_video_views = UserVideoProgress.objects.filter(watched=True).count()
        total_video_watches = UserVideoProgress.objects.count()
        
        # Kategoriya bo'yicha test natijalari
        category_test_stats = Category.objects.annotate(
            test_count=Count('tests', filter=Q(tests__is_active=True)),
            result_count=Count('tests__results', filter=Q(tests__results__completed_at__isnull=False)),
            avg_score=Avg('tests__results__percentage', filter=Q(tests__results__completed_at__isnull=False)),
        ).order_by('order')
        
        # Eng ko'p ishlangan testlar
        popular_tests = Test.objects.annotate(
            result_count=Count('results', filter=Q(results__completed_at__isnull=False)),
            avg_score=Avg('results__percentage', filter=Q(results__completed_at__isnull=False))
        ).filter(result_count__gt=0).order_by('-result_count')[:10]
        
        # Eng ko'p ko'rilgan videolar
        popular_videos = VideoLesson.objects.annotate(
            view_count=Count('progress', filter=Q(progress__watched=True))
        ).filter(view_count__gt=0).order_by('-view_count')[:10]
        
        # Foydalanuvchilar bo'yicha statistikalar
        top_users = User.objects.annotate(
            test_count=Count('test_results', filter=Q(test_results__completed_at__isnull=False)),
            avg_score=Avg('test_results__percentage', filter=Q(test_results__completed_at__isnull=False)),
            video_count=Count('video_progress', filter=Q(video_progress__watched=True))
        ).filter(test_count__gt=0).order_by('-test_count')[:10]
        
        # Oxirgi 30 kundagi faollik
        recent_activities = UserActivity.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values('activity_type').annotate(count=Count('id')).order_by('-count')
        
        context = {
            **self.each_context(request),
            'total_users': total_users,
            'active_users_30d': active_users_30d,
            'active_users_7d': active_users_7d,
            'active_users_365d': active_users_365d,
            'total_tests': total_tests,
            'total_test_results': total_test_results,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'avg_score': round(avg_score, 2),
            'total_videos': total_videos,
            'total_video_views': total_video_views,
            'total_video_watches': total_video_watches,
            'category_test_stats': category_test_stats,
            'popular_tests': popular_tests,
            'popular_videos': popular_videos,
            'top_users': top_users,
            'recent_activities': recent_activities,
        }
        
        return render(request, 'admin/statistics.html', context)


# Custom Admin Index View
def custom_admin_index(request):
    """Admin index sahifasini yaxshilash"""
    # Asosiy statistikalar
    total_users = User.objects.count()
    total_tests = Test.objects.filter(is_active=True).count()
    total_videos = VideoLesson.objects.filter(is_active=True).count()
    total_test_results = UserTestResult.objects.filter(completed_at__isnull=False).count()
    total_video_views = UserVideoProgress.objects.filter(watched=True).count()
    
    # Oxirgi test natijalari
    recent_results = UserTestResult.objects.filter(
        completed_at__isnull=False
    ).select_related('user', 'test', 'test__category').order_by('-completed_at')[:10]
    
    # Oxirgi video ko'rishlar
    recent_video_views = UserVideoProgress.objects.filter(
        watched=True
    ).select_related('user', 'video', 'video__category').order_by('-completed_at')[:10]
    
    period_days = parse_active_users_period(request)
    active_users = build_active_users_report(days=period_days)
    active_users_summary = build_active_users_summary()
    active_users_total_in_period = next(
        (x['count'] for x in active_users_summary if x['days'] == period_days),
        count_active_users(period_days),
    )
    active_month_labels, active_month_counts = build_active_users_monthly_trend(days=min(period_days, 365))
    
    passed_tests = UserTestResult.objects.filter(
        completed_at__isnull=False,
        percentage__gte=F('test__passing_score'),
    ).count()
    failed_tests = max(total_test_results - passed_tests, 0)

    avg_score = UserTestResult.objects.filter(
        completed_at__isnull=False
    ).aggregate(avg=Avg('percentage'))['avg'] or 0

    category_test_stats = Category.objects.filter(is_active=True).annotate(
        test_count=Count('tests', filter=Q(tests__is_active=True), distinct=True),
        result_count=Count('tests__results', filter=Q(tests__results__completed_at__isnull=False), distinct=True),
        avg_score=Avg('tests__results__percentage', filter=Q(tests__results__completed_at__isnull=False))
    ).order_by('order')
    
    context = {
        'total_users': total_users,
        'total_tests': total_tests,
        'total_videos': total_videos,
        'total_test_results': total_test_results,
        'total_video_views': total_video_views,
        'recent_results': recent_results,
        'recent_video_views': recent_video_views,
        'active_users': active_users,
        'active_users_period_days': period_days,
        'active_users_summary_list': active_users_summary,
        'active_users_total_in_period': active_users_total_in_period,
        'active_users_period_choices': ACTIVE_USERS_PERIOD_CHOICES,
        'active_month_labels': active_month_labels,
        'active_month_counts': active_month_counts,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'avg_score': round(avg_score, 2),
        'category_test_stats': category_test_stats,
    }
    
    # Django admin index template ni override qilish
    from django.contrib.admin.views.decorators import staff_member_required
    from django.contrib.admin import site
    
    return render(request, 'admin/index.html', {
        **site.each_context(request),
        **context,
    })


# Admin index ni override qilish
admin.site.index_template = 'admin/custom_index.html'
admin.site.site_header = "IELTS Center - Admin Panel"
admin.site.site_title = "IELTS Admin"
admin.site.index_title = "Boshqaruv paneli"

# Admin index view ni override qilish
original_index = admin.site.index
original_get_app_list = admin.site.get_app_list


def custom_get_app_list(self, request, app_label=None):
    """
    Sidebar va admin index ro'yxatini mantiqiy bo'limlarga ajratish:
    - IELTS
    - SAT
    - RUXSATLAR
    """
    app_list = original_get_app_list(request, app_label)

    core_app = None
    remaining_apps = []
    for app in app_list:
        if app.get('app_label') == 'core':
            core_app = app
        else:
            remaining_apps.append(app)

    if not core_app:
        return app_list

    sat_model_names = {'SATResource', 'SATResourceProgress', 'SATResourceBookmark', 'SATResourceNote'}
    permission_model_names = {'UserModuleAccess'}

    ielts_models = []
    sat_models = []
    permission_models = []

    for model in core_app.get('models', []):
        object_name = model.get('object_name')
        if object_name in sat_model_names:
            sat_models.append(model)
        elif object_name in permission_model_names:
            permission_models.append(model)
        else:
            ielts_models.append(model)

    split_apps = []
    if ielts_models:
        split_apps.append({
            'name': 'IELTS - Testlar va videolar',
            'app_label': 'core_ielts',
            'app_url': core_app.get('app_url', '#'),
            'has_module_perms': core_app.get('has_module_perms', True),
            'models': sorted(ielts_models, key=lambda m: m.get('name', '')),
        })

    if sat_models:
        split_apps.append({
            'name': 'SAT - Resurslar',
            'app_label': 'core_sat',
            'app_url': core_app.get('app_url', '#'),
            'has_module_perms': core_app.get('has_module_perms', True),
            'models': sorted(sat_models, key=lambda m: m.get('name', '')),
        })

    if permission_models:
        split_apps.append({
            'name': 'RUXSATLAR',
            'app_label': 'core_permissions',
            'app_url': core_app.get('app_url', '#'),
            'has_module_perms': core_app.get('has_module_perms', True),
            'models': sorted(permission_models, key=lambda m: m.get('name', '')),
        })

    return split_apps + remaining_apps

def custom_index(request, extra_context=None):
    """Admin index sahifasini yaxshilash"""
    # Asosiy statistikalar
    total_users = User.objects.count()
    total_tests = Test.objects.filter(is_active=True).count()
    total_videos = VideoLesson.objects.filter(is_active=True).count()
    total_test_results = UserTestResult.objects.filter(completed_at__isnull=False).count()
    total_video_views = UserVideoProgress.objects.filter(watched=True).count()
    
    # Oxirgi test natijalari
    recent_results = UserTestResult.objects.filter(
        completed_at__isnull=False
    ).select_related('user', 'test', 'test__category').order_by('-completed_at')[:10]
    
    # Oxirgi video ko'rishlar
    recent_video_views = UserVideoProgress.objects.filter(
        watched=True
    ).select_related('user', 'video', 'video__category').order_by('-completed_at')[:10]
    
    period_days = parse_active_users_period(request)
    active_users = build_active_users_report(days=period_days)
    active_users_summary = build_active_users_summary()
    active_users_total_in_period = next(
        (x['count'] for x in active_users_summary if x['days'] == period_days),
        count_active_users(period_days),
    )
    active_month_labels, active_month_counts = build_active_users_monthly_trend(days=min(period_days, 365))

    # O'tdi/O'tmadi statistikasi (DB da — barcha natijalarni xotiraga yuklamasdan)
    passed_tests = UserTestResult.objects.filter(
        completed_at__isnull=False,
        percentage__gte=F('test__passing_score'),
    ).count()
    failed_tests = max(total_test_results - passed_tests, 0)

    avg_score = UserTestResult.objects.filter(
        completed_at__isnull=False
    ).aggregate(avg=Avg('percentage'))['avg'] or 0

    # Kategoriya bo'yicha statistikalar
    category_test_stats = list(
        Category.objects.filter(is_active=True).annotate(
            test_count=Count('tests', filter=Q(tests__is_active=True), distinct=True),
            result_count=Count('tests__results', filter=Q(tests__results__completed_at__isnull=False), distinct=True),
            avg_score=Avg('tests__results__percentage', filter=Q(tests__results__completed_at__isnull=False))
        ).order_by('order').values('name', 'test_count', 'result_count', 'avg_score')
    )

    # Oxirgi 14 kunlik trend (test yakunlashlar soni)
    start_date = timezone.now() - timedelta(days=13)
    daily_map = {
        row['day']: row['count']
        for row in UserTestResult.objects.filter(
            completed_at__isnull=False,
            completed_at__gte=start_date
        ).annotate(day=TruncDate('completed_at')).values('day').annotate(count=Count('id'))
    }
    trend_labels = []
    trend_counts = []
    for i in range(14):
        d = (start_date + timedelta(days=i)).date()
        trend_labels.append(d.strftime('%d.%m'))
        trend_counts.append(daily_map.get(d, 0))

    chart_payload = {
        'pass_fail': [passed_tests, failed_tests],
        'category_labels': [c['name'] for c in category_test_stats],
        'category_tests': [c['test_count'] or 0 for c in category_test_stats],
        'category_results': [c['result_count'] or 0 for c in category_test_stats],
        'trend_labels': trend_labels,
        'trend_counts': trend_counts,
        'active_month_labels': active_month_labels,
        'active_month_counts': active_month_counts,
    }
    
    extra_context = extra_context or {}
    extra_context.update({
        'total_users': total_users,
        'total_tests': total_tests,
        'total_videos': total_videos,
        'total_test_results': total_test_results,
        'total_video_views': total_video_views,
        'recent_results': recent_results,
        'recent_video_views': recent_video_views,
        'active_users': active_users,
        'active_users_period_days': period_days,
        'active_users_summary_list': active_users_summary,
        'active_users_total_in_period': active_users_total_in_period,
        'active_users_period_choices': ACTIVE_USERS_PERIOD_CHOICES,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'avg_score': round(avg_score, 2),
        'category_test_stats': category_test_stats,
        'chart_payload_json': json.dumps(chart_payload),
    })
    
    return original_index(request, extra_context=extra_context)

admin.site.index = custom_index
admin.site.get_app_list = MethodType(custom_get_app_list, admin.site)
