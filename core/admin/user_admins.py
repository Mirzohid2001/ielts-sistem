"""Foydalanuvchi natijalari, video progress, flashcard va hokazo."""
from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

from ..models import (
    Bookmark,
    Flashcard,
    FlashcardSet,
    PlaylistVideo,
    StudyStreak,
    UserActivity,
    UserTestAnswer,
    UserTestResult,
    UserVideoProgress,
    VideoComment,
    VideoNote,
    VideoPlaylist,
    VideoRating,
)


# UserTestAnswer Inline
class UserTestAnswerInline(admin.TabularInline):
    model = UserTestAnswer
    extra = 0
    readonly_fields = ['question', 'user_answer', 'answered_at']
    can_delete = False
    # is_correct – tahrirlash mumkin (essay baholash uchun). O'zgartirsangiz "Qayta hisoblash" actionini ishlating.


# UserTestResult Admin - Yaxshilangan
@admin.register(UserTestResult)
class UserTestResultAdmin(ImportExportModelAdmin):
    list_display = ['user', 'test', 'score', 'total_questions', 'percentage', 'correct_answers', 'attempt_number', 'is_passed_display', 'completed_at']
    list_filter = ['test', 'test__category', 'completed_at', 'started_at', 'test__test_type', 'is_paused']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'test__title']
    readonly_fields = ['score', 'percentage', 'correct_answers', 'wrong_answers', 'answers_json', 'attempt_number', 'started_at', 'completed_at']
    ordering = ['-completed_at', '-started_at']
    inlines = [UserTestAnswerInline]
    list_per_page = 50
    autocomplete_fields = ['user', 'test']
    date_hierarchy = 'completed_at'
    actions = ['recalculate_selected_results']
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('user', 'test')
        }),
        ('Natija', {
            'fields': ('score', 'total_questions', 'percentage', 'correct_answers', 'wrong_answers', 'time_taken', 'attempt_number')
        }),
        ('Vaqt', {
            'fields': ('started_at', 'completed_at')
        }),
        ('Javoblar', {
            'fields': ('answers_json',)
        }),
    )
    
    def is_passed_display(self, obj):
        if obj.is_passed():
            return format_html('<span style="color: green; font-weight: bold;">✓ O\'tdi</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ O\'tmadi</span>')
    is_passed_display.short_description = "Holat"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'test', 'test__category')

    @admin.action(description="Tanlangan natijalarni qayta hisoblash")
    def recalculate_selected_results(self, request, queryset):
        updated = 0
        for result in queryset.select_related('test'):
            result.total_questions = result.total_questions or (result.test.total_questions if result.test else 0)
            result.recalculate_from_answers()
            updated += 1
        self.message_user(request, f"{updated} ta natija qayta hisoblandi.")


@admin.register(UserTestAnswer)
class UserTestAnswerAdmin(admin.ModelAdmin):
    list_display = ['test_result', 'question_type_display', 'user_answer_short', 'is_correct', 'answered_at']
    list_editable = ['is_correct']
    list_filter = ['is_correct', 'answered_at', 'question__question_type', 'question__test__test_type']
    search_fields = ['test_result__user__username', 'question__question_text', 'user_answer']
    readonly_fields = ['answered_at']
    autocomplete_fields = ['test_result', 'question']
    ordering = ['-answered_at']
    list_per_page = 50

    def question_type_display(self, obj):
        return obj.question.get_question_type_display() if obj.question_id else '-'

    question_type_display.short_description = "Tur"

    def user_answer_short(self, obj):
        t = (obj.user_answer or '')[:60]
        return (t + '...') if len(obj.user_answer or '') > 60 else t

    user_answer_short.short_description = "Javob"


# UserVideoProgress Admin - Yaxshilangan
@admin.register(UserVideoProgress)
class UserVideoProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'category_display', 'watched', 'watch_percentage', 'last_watched_at', 'completed_at']
    list_filter = ['watched', 'video__category', 'last_watched_at', 'completed_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'video__title']
    readonly_fields = ['last_watched_at', 'completed_at']
    ordering = ['-last_watched_at']
    list_per_page = 50
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('user', 'video')
        }),
        ('Progress', {
            'fields': ('watched', 'watch_percentage', 'last_watched_at', 'completed_at')
        }),
    )
    
    def category_display(self, obj):
        return obj.video.category.name if obj.video.category else "-"
    category_display.short_description = "Kategoriya"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'video', 'video__category')


# UserActivity Admin
@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'related_object_type', 'created_at']
    list_filter = ['activity_type', 'related_object_type', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    list_per_page = 100
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('user', 'activity_type')
        }),
        ('Bog\'liq obyekt', {
            'fields': ('related_object_type', 'related_object_id', 'metadata')
        }),
        ('Vaqt', {
            'fields': ('created_at',)
        }),
    )


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'test', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'video__title', 'test__title']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(StudyStreak)
class StudyStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'activities_count', 'created_at']
    list_filter = ['date', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at']
    ordering = ['-date', '-created_at']


@admin.register(VideoNote)
class VideoNoteAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'timestamp_display', 'note_text_short', 'created_at']
    list_filter = ['video', 'created_at']
    search_fields = ['user__username', 'video__title', 'note_text']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def timestamp_display(self, obj):
        return obj.get_timestamp_display()
    timestamp_display.short_description = "Vaqt"
    
    def note_text_short(self, obj):
        return obj.note_text[:50] + "..." if len(obj.note_text) > 50 else obj.note_text
    note_text_short.short_description = "Eslatma"


@admin.register(VideoRating)
class VideoRatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'video__title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'comment_text_short', 'parent', 'is_edited', 'created_at']
    list_filter = ['video', 'is_edited', 'created_at']
    search_fields = ['user__username', 'video__title', 'comment_text']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def comment_text_short(self, obj):
        return obj.comment_text[:50] + "..." if len(obj.comment_text) > 50 else obj.comment_text
    comment_text_short.short_description = "Izoh"


class PlaylistVideoInline(admin.TabularInline):
    model = PlaylistVideo
    extra = 1
    fields = ['video', 'order']
    ordering = ['order']


@admin.register(VideoPlaylist)
class VideoPlaylistAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'videos_count', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'user__username', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PlaylistVideoInline]
    ordering = ['-created_at']
    
    def videos_count(self, obj):
        return obj.videos_count
    videos_count.short_description = "Videolar soni"


@admin.register(FlashcardSet)
class FlashcardSetAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'cards_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'user__username']
    autocomplete_fields = ['user']
    ordering = ['name', '-created_at']

    def cards_count(self, obj):
        return obj.cards.count()
    cards_count.short_description = "Cardlar"


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ['term_short', 'flashcard_set', 'user', 'source_test', 'created_at']
    list_filter = ['flashcard_set', 'created_at']
    search_fields = ['term', 'definition', 'user__username', 'flashcard_set__name']
    autocomplete_fields = ['user', 'flashcard_set', 'source_test', 'source_question']
    ordering = ['-created_at']
    list_per_page = 50

    def term_short(self, obj):
        return obj.term[:60] + "..." if len(obj.term) > 60 else obj.term
    term_short.short_description = "Term"
