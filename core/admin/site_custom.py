"""Admin bosh sahifa va index override (CustomAdminSite — kelajakda statistics URL uchun)."""
import json
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Avg, Count, F, Q
from django.db.models.functions import TruncDate
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
        active_users_30d = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        active_users_7d = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=7)
        ).count()
        
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
    
    # Eng faol foydalanuvchilar (oxirgi 7 kun)
    active_users = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(days=7)
    ).annotate(
        test_count=Count('test_results', filter=Q(test_results__completed_at__isnull=False)),
        video_count=Count('video_progress', filter=Q(video_progress__watched=True))
    ).order_by('-last_login')[:10]
    
    # Chartlar uchun ma'lumotlar
    # Test natijalari (o'tgan/o'tmagan)
    # Har bir test natijasini alohida tekshirish kerak
    all_results = UserTestResult.objects.filter(
        completed_at__isnull=False
    ).select_related('test')
    passed_tests = sum(1 for r in all_results if r.is_passed())
    failed_tests = total_test_results - passed_tests
    
    # O'rtacha ball
    avg_score = UserTestResult.objects.filter(
        completed_at__isnull=False
    ).aggregate(avg=Avg('percentage'))['avg'] or 0
    
    # Kategoriya bo'yicha statistikalar
    # Barcha kategoriyalarni olish, hatto testlari bo'lmasa ham
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
    
    # Eng faol foydalanuvchilar (oxirgi 7 kun)
    active_users = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(days=7)
    ).annotate(
        test_count=Count('test_results', filter=Q(test_results__completed_at__isnull=False)),
        video_count=Count('video_progress', filter=Q(video_progress__watched=True))
    ).order_by('-last_login')[:10]

    # O'tdi/O'tmadi statistikasi
    all_results = UserTestResult.objects.filter(
        completed_at__isnull=False
    ).select_related('test')
    passed_tests = sum(1 for r in all_results if r.is_passed())
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
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'avg_score': round(avg_score, 2),
        'category_test_stats': category_test_stats,
        'chart_payload_json': json.dumps(chart_payload),
    })
    
    return original_index(request, extra_context=extra_context)

admin.site.index = custom_index
