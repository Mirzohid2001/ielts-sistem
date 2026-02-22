from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from django.db.models.functions import TruncDate
from datetime import timedelta
import json
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import (
    Category, VideoLesson, Test, Question,
    UserTestResult, UserTestAnswer, UserVideoProgress, UserActivity,
    Bookmark, StudyStreak, VideoNote, VideoRating,
    VideoComment, VideoPlaylist, PlaylistVideo, FlashcardSet, Flashcard
)
from django.contrib.auth.models import User


class TestResource(resources.ModelResource):
    class Meta:
        model = Test
        fields = (
            'id', 'title', 'category__name', 'test_type', 'difficulty', 'duration_minutes',
            'passing_score', 'allow_retake', 'max_attempts', 'is_active', 'created_at'
        )


class QuestionResource(resources.ModelResource):
    class Meta:
        model = Question
        fields = (
            'id', 'test__title', 'order', 'question_type', 'question_text',
            'correct_answer', 'points', 'created_at'
        )


class QuestionAdminForm(forms.ModelForm):
    """Savol turiga qarab admin validatsiya."""
    instruction_text = forms.CharField(
        required=False,
        label="Ko'rsatma (Instruction)",
        help_text="Masalan: ONE WORD ONLY",
    )
    fill_answers = forms.CharField(
        required=False,
        label="Fill javoblari",
        help_text="Bir nechta javob bo'lsa vergul bilan yozing. Masalan: smart,fuel,waiting",
    )
    matching_items = forms.CharField(
        required=False,
        label="Matching itemlar",
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text="Har satr: 1|Paragraph A",
    )
    matching_options = forms.CharField(
        required=False,
        label="Matching variantlar",
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text="Har satr: A|Heading text",
    )
    matching_correct = forms.CharField(
        required=False,
        label="Matching to'g'ri javob",
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text="Har satr: 1:A",
    )
    list_options_simple = forms.CharField(
        required=False,
        label="List options",
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text="Har satr: A|Option text",
    )
    list_correct_simple = forms.CharField(
        required=False,
        label="List to'g'ri javob",
        help_text="Masalan: A,C",
    )

    class Meta:
        model = Question
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inst = self.instance
        opts = inst.options_json or {}
        corr = inst.correct_answer_json

        self.fields['instruction_text'].initial = opts.get('instruction', '')

        if inst.question_type in ('fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 'table_completion', 'short_answer'):
            if isinstance(corr, list):
                self.fields['fill_answers'].initial = ', '.join(str(x) for x in corr)
            elif inst.correct_answer:
                self.fields['fill_answers'].initial = inst.correct_answer

        if inst.question_type in ('matching_headings', 'matching_features', 'matching_info', 'matching_sentences', 'classification'):
            items = opts.get('items', [])
            headings = opts.get('headings', [])
            if items:
                self.fields['matching_items'].initial = "\n".join(
                    f"{i.get('num', idx+1)}|{i.get('label', '')}" for idx, i in enumerate(items) if isinstance(i, dict)
                )
            if headings:
                self.fields['matching_options'].initial = "\n".join(
                    f"{h.get('letter', '')}|{h.get('text', '')}" for h in headings if isinstance(h, dict)
                )
            if isinstance(corr, dict):
                self.fields['matching_correct'].initial = "\n".join(f"{k}:{v}" for k, v in corr.items())

        if inst.question_type == 'list_selection':
            options = opts.get('options', [])
            if options:
                self.fields['list_options_simple'].initial = "\n".join(
                    f"{o.get('letter', '')}|{o.get('text', '')}" for o in options if isinstance(o, dict)
                )
            if isinstance(corr, list):
                self.fields['list_correct_simple'].initial = ",".join(str(x) for x in corr)

    def clean(self):
        cleaned = super().clean()
        q_type = cleaned.get('question_type')
        correct_answer = (cleaned.get('correct_answer') or '').strip().lower()
        correct_json = cleaned.get('correct_answer_json')
        options_json = cleaned.get('options_json') or {}
        instruction_text = (cleaned.get('instruction_text') or '').strip()
        fill_answers = (cleaned.get('fill_answers') or '').strip()
        matching_items = (cleaned.get('matching_items') or '').strip()
        matching_options = (cleaned.get('matching_options') or '').strip()
        matching_correct = (cleaned.get('matching_correct') or '').strip()
        list_options_simple = (cleaned.get('list_options_simple') or '').strip()
        list_correct_simple = (cleaned.get('list_correct_simple') or '').strip()

        single_choice = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
        fill_types = ('fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 'table_completion', 'short_answer')
        matching_types = ('matching_headings', 'matching_features', 'matching_info', 'matching_sentences', 'classification')

        if instruction_text:
            options_json['instruction'] = instruction_text

        if q_type in fill_types and fill_answers:
            parsed = [x.strip() for x in fill_answers.replace('\n', ',').split(',') if x.strip()]
            if parsed:
                cleaned['correct_answer_json'] = parsed
                options_json['blanks_count'] = len(parsed)
                correct_json = parsed

        if q_type in matching_types and (matching_items or matching_options or matching_correct):
            items = []
            for idx, line in enumerate([ln.strip() for ln in matching_items.splitlines() if ln.strip()]):
                if '|' in line:
                    left, right = line.split('|', 1)
                    left = left.strip()
                    right = right.strip()
                    num = int(left) if left.isdigit() else (idx + 1)
                    items.append({'num': num, 'label': right})
                else:
                    items.append({'num': idx + 1, 'label': line})

            headings = []
            for line in [ln.strip() for ln in matching_options.splitlines() if ln.strip()]:
                if '|' in line:
                    letter, text = line.split('|', 1)
                    headings.append({'letter': letter.strip(), 'text': text.strip()})

            corr_map = {}
            for line in [ln.strip() for ln in matching_correct.splitlines() if ln.strip()]:
                if ':' in line:
                    k, v = line.split(':', 1)
                    corr_map[k.strip()] = v.strip()

            if items:
                options_json['items'] = items
            if headings:
                options_json['headings'] = headings
            if corr_map:
                cleaned['correct_answer_json'] = corr_map
                correct_json = corr_map

        if q_type == 'list_selection' and (list_options_simple or list_correct_simple):
            options = []
            for line in [ln.strip() for ln in list_options_simple.splitlines() if ln.strip()]:
                if '|' in line:
                    letter, text = line.split('|', 1)
                    options.append({'letter': letter.strip(), 'text': text.strip()})
                else:
                    options.append({'letter': line[:1].upper(), 'text': line})

            corr_list = [x.strip() for x in list_correct_simple.replace(' ', '').split(',') if x.strip()]
            if options:
                options_json['options'] = options
            if corr_list:
                cleaned['correct_answer_json'] = corr_list
                correct_json = corr_list

        cleaned['options_json'] = options_json

        if q_type in single_choice:
            allowed_map = {
                'mcq': {'a', 'b', 'c', 'd'},
                'true_false': {'a', 'b'},
                'true_false_not_given': {'a', 'b', 'c'},
                'yes_no_not_given': {'a', 'b', 'c'},
            }
            if not correct_answer:
                raise forms.ValidationError("Bu savol turida 'To'g'ri javob' maydoni majburiy.")
            if correct_answer not in allowed_map.get(q_type, set()):
                raise forms.ValidationError("To'g'ri javob qiymati savol turiga mos emas.")

        if q_type in fill_types:
            if not correct_json and not correct_answer:
                raise forms.ValidationError("Fill-in turlarida correct_answer_json yoki correct_answer kiriting.")
            if correct_json and not isinstance(correct_json, list):
                raise forms.ValidationError("Fill-in turlarida correct_answer_json ro'yxat (list) bo'lishi kerak.")

        if q_type in matching_types:
            if not isinstance(correct_json, dict) or not correct_json:
                raise forms.ValidationError("Matching/Classification turlarida correct_answer_json obyekt (dict) bo'lishi kerak.")

        if q_type == 'list_selection':
            if not isinstance(correct_json, list) or not correct_json:
                raise forms.ValidationError("List selection uchun correct_answer_json ro'yxat (list) bo'lishi kerak.")

        return cleaned


# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'color_display', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = "Rang"


# VideoLesson Admin
@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'youtube_id', 'duration_display', 'views_count', 'is_active', 'created_at']
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
        ('YouTube', {
            'fields': ('youtube_url', 'youtube_id', 'youtube_thumbnail', 'duration')
        }),
        ('Tartib', {
            'fields': ('order',)
        }),
        ('Statistika', {
            'fields': ('views_count', 'created_at', 'updated_at')
        }),
    )
    
    def duration_display(self, obj):
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            return f"{minutes}:{seconds:02d}"
        return "-"
    duration_display.short_description = "Davomiyligi"


# Question Inline - StackedInline - savol qo'shish qulayroq
class QuestionInline(admin.StackedInline):
    model = Question
    form = QuestionAdminForm
    extra = 1
    fields = [
        'order', 'question_type', 'question_text',
        ('option_a', 'option_b', 'option_c', 'option_d'),
        'correct_answer', 'instruction_text', 'fill_answers', 'points', 'explanation'
    ]
    classes = ['collapse']
    verbose_name = "Savol"
    verbose_name_plural = "Savollar"
    show_change_link = True  # Savolni alohida sahifada tahrirlash mumkin


# Test Admin - yaxshilangan
@admin.register(Test)
class TestAdmin(ImportExportModelAdmin):
    list_display = ['title', 'category', 'test_type', 'difficulty', 'total_questions_display', 'duration_minutes', 'passing_score', 'is_active', 'created_at']
    list_filter = ['category', 'test_type', 'difficulty', 'allow_retake', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-created_at']
    list_editable = ['is_active']
    list_per_page = 25
    inlines = [QuestionInline]
    autocomplete_fields = ['category']
    list_select_related = ['category']
    save_as = True
    save_on_top = True
    date_hierarchy = 'created_at'
    resource_class = TestResource

    actions = ['duplicate_tests', 'activate_tests', 'deactivate_tests']

    class Media:
        js = ('core/js/question_admin.js',)
        css = {'all': ('core/css/question_admin.css',)}

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('title', 'category', 'test_type', 'difficulty', 'description', 'is_active')
        }),
        ('Parametrlar', {
            'fields': ('duration_minutes', 'passing_score', 'allow_retake', 'max_attempts'),
            'description': 'duration_minutes - daqiqada. passing_score - foizda (masalan 60).'
        }),
        ('Test kontenti', {
            'fields': ('audio_file', 'reading_text'),
            'description': 'Listening: audio fayl yuklang. Reading: matn kiriting.'
        }),
    )

    def total_questions_display(self, obj):
        count = obj.total_questions
        return format_html('<strong>{}</strong>', count)
    total_questions_display.short_description = "Savollar"

    @admin.action(description="Testni nusxalash")
    def duplicate_tests(self, request, queryset):
        for test in queryset:
            questions = list(test.questions.all().order_by('order'))
            test.pk = None
            test._state.adding = True
            test.title = f"{test.title} (nusxa)"
            test.save()
            for q in questions:
                q.pk = None
                q.test = test
                q._state.adding = True
                q.save()
        self.message_user(request, f"{queryset.count()} ta test nusxalandi.")

    @admin.action(description="Faollashtirish")
    def activate_tests(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} ta test faollashtirildi.")

    @admin.action(description="O'chirish (faol emas)")
    def deactivate_tests(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f"{n} ta test o'chirildi.")


# Question Admin - savol qo'shish qulay
@admin.register(Question)
class QuestionAdmin(ImportExportModelAdmin):
    form = QuestionAdminForm
    list_display = ['test', 'order', 'question_type', 'question_text_short', 'correct_answer', 'points', 'created_at']
    list_filter = ['test__category', 'question_type', 'created_at']
    search_fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d']
    ordering = ['test', 'order']
    list_per_page = 30
    autocomplete_fields = ['test']
    list_select_related = ['test', 'test__category']
    save_as = True
    save_on_top = True
    resource_class = QuestionResource

    fieldsets = (
        ('Asosiy', {
            'fields': ('test', 'order', 'question_type', 'question_text', 'question_image', 'points')
        }),
        ('MCQ / True-False / Yes-No-Not Given', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer'),
            'classes': ('question-mcq-fields',),
            'description': 'MCQ: A/B/C/D. True/False: A=True, B=False. Yes/No/Not Given: A=Yes, B=No, C=Not Given.'
        }),
        ('Fill-in / Matching / List Selection (Oddiy rejim)', {
            'fields': (
                'instruction_text',
                'fill_answers',
                'matching_items',
                'matching_options',
                'matching_correct',
                'list_options_simple',
                'list_correct_simple',
            ),
            'classes': ('question-fill-fields',),
            'description': 'JSON bilmasangiz shu maydonlarni to\'ldiring. Tizim JSON ni o\'zi yig\'adi.'
        }),
        ('Advanced JSON (ixtiyoriy)', {
            'fields': ('correct_answer_json', 'options_json'),
            'classes': ('collapse',),
            'description': 'Faqat power-userlar uchun. Oddiy rejim yetarli.'
        }),
        ('Tushuntirish va Listening', {
            'fields': ('explanation', 'audio_timestamp')
        }),
    )

    class Media:
        js = ('core/js/question_admin.js',)
        css = {'all': ('core/css/question_admin.css',)}

    def question_text_short(self, obj):
        t = obj.question_text or ''
        return (t[:80] + '...') if len(t) > 80 else t
    question_text_short.short_description = "Savol"


# UserTestAnswer Inline
class UserTestAnswerInline(admin.TabularInline):
    model = UserTestAnswer
    extra = 0
    readonly_fields = ['question', 'user_answer', 'is_correct', 'answered_at']
    can_delete = False


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
            total_questions = result.test.total_questions
            correct = result.answers.filter(is_correct=True).count()
            result.total_questions = total_questions
            result.correct_answers = correct
            result.wrong_answers = max(total_questions - correct, 0)
            result.calculate_score()
            updated += 1
        self.message_user(request, f"{updated} ta natija qayta hisoblandi.")


@admin.register(UserTestAnswer)
class UserTestAnswerAdmin(admin.ModelAdmin):
    list_display = ['test_result', 'question', 'is_correct', 'answered_at']
    list_filter = ['is_correct', 'answered_at', 'question__question_type', 'question__test__test_type']
    search_fields = ['test_result__user__username', 'question__question_text', 'user_answer']
    readonly_fields = ['answered_at']
    autocomplete_fields = ['test_result', 'question']
    ordering = ['-answered_at']
    list_per_page = 50


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
            score__gte=Q(test__passing_score)
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
            test_count=Count('test', filter=Q(test__is_active=True)),
            result_count=Count('test__results', filter=Q(test__results__completed_at__isnull=False)),
            avg_score=Avg('test__results__percentage', filter=Q(test__results__completed_at__isnull=False))
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
