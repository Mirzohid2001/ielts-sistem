"""Kategoriya, savol turi qoidalari, video darslar."""
from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from ..models import Category, QuestionTypeRule, VideoLesson


# Category Admin — testlar va videolar uchun kategoriya
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'tests_count_display', 'videos_count_display', 'icon', 'color_display', 'order', 'is_active', 'show_on_site', 'created_at']
    list_filter = ['parent', 'is_active', 'show_on_site', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    list_editable = ['order', 'is_active', 'show_on_site']

    fields = (
        'name',
        'slug',
        'parent',
        'description',
        'icon',
        'color',
        'order',
        'is_active',
        'show_on_site',
    )

    def tests_count_display(self, obj):
        c = getattr(obj, '_tests', None)
        if c is not None:
            return c
        return obj.tests.filter(is_active=True).count() if hasattr(obj, 'tests') else 0
    tests_count_display.short_description = "Testlar"

    def videos_count_display(self, obj):
        c = getattr(obj, '_videos', None)
        if c is not None:
            return c
        return obj.videos.filter(is_active=True).count() if hasattr(obj, 'videos') else 0
    videos_count_display.short_description = "Videolar"

    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = "Rang"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _tests=Count('tests', filter=Q(tests__is_active=True)),
            _videos=Count('videos', filter=Q(videos__is_active=True)),
        )


# Savol turi qoidalari — har bir savol TURI uchun bitta shart (klient tahrirlaydi)
@admin.register(QuestionTypeRule)
class QuestionTypeRuleAdmin(admin.ModelAdmin):
    list_display = ['question_type', 'name_uz', 'shart_short', 'order']
    list_editable = ['order']
    search_fields = ['question_type', 'name_uz', 'shart_text']
    ordering = ['order', 'question_type']

    def shart_short(self, obj):
        t = (obj.shart_text or '')[:80]
        return f"{t}..." if len(obj.shart_text or '') > 80 else t
    shart_short.short_description = "Shart (qisqa)"


# VideoLesson Admin
@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'video_source_display', 'duration_display', 'views_count', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'youtube_id']
    ordering = ['order', 'created_at']
    readonly_fields = ['youtube_id', 'youtube_thumbnail', 'views_count', 'created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        """Admin panelda saqlashda YouTube ID ni yangilash"""
        if obj.youtube_url:
            extracted_id = obj.extract_youtube_id(obj.youtube_url)
            if extracted_id and len(extracted_id) == 11:
                obj.youtube_id = extracted_id
                if not obj.youtube_thumbnail:
                    obj.youtube_thumbnail = f"https://img.youtube.com/vi/{obj.youtube_id}/maxresdefault.jpg"
            elif not extracted_id:
                # Agar extract qilinmasa, youtube_id ni tozalash
                obj.youtube_id = ''
        super().save_model(request, obj, form, change)
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('title', 'category', 'description', 'is_active')
        }),
        ('Video (afzallik: yuklangan fayl)', {
            'fields': ('video_file', 'cover_image', 'duration'),
            'description': 'Video fayl yuklasangiz, saytda shu video ko\'rsatiladi. Obloshka — kartochkada ko\'rinadigan rasm.'
        }),
        ('YouTube (ixtiyoriy)', {
            'fields': ('youtube_url', 'youtube_id', 'youtube_thumbnail'),
            'description': 'Agar video fayl yuklanmagan bo\'lsa, YouTube link orqali ko\'rsatiladi.'
        }),
        ('Tartib', {
            'fields': ('order',)
        }),
        ('Statistika', {
            'fields': ('views_count', 'created_at', 'updated_at')
        }),
    )
    
    def video_source_display(self, obj):
        if obj.video_file:
            return "Fayl"
        if obj.youtube_id:
            return "YouTube"
        return "-"
    video_source_display.short_description = "Manba"

    def duration_display(self, obj):
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            return f"{minutes}:{seconds:02d}"
        return "-"
    duration_display.short_description = "Davomiyligi"
