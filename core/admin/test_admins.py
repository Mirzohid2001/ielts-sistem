"""Test, savol, passage admin (Reading / Listening / Writing — barcha turlar)."""
from django.contrib import admin
from django import forms
from django.contrib import messages
from django.db import transaction
from django.utils.html import format_html
from django.core.management import call_command
from import_export.admin import ImportExportModelAdmin

from .forms import QuestionAdminForm, QuestionResource, TestResource, question_type_rules_json
from ..models import Question, ReadingPassage, Test


# Question Inline - StackedInline - savol qo'shish qulayroq
# extra=0: yangi test qo'shanda bo'sh savol qatori bo'lmaydi — avval testni saqlang, keyin savollar qo'shing
class QuestionInline(admin.StackedInline):
    model = Question
    form = QuestionAdminForm
    extra = 0
    min_num = 0
    ordering = ['order', 'pk']
    classes = []  # ochiq — savollar yopiq bo'lmasin
    verbose_name = "Savol"
    verbose_name_plural = (
        "📝 2-QADAM: Savollar — «Yana bir Savol qo'shish» dan qo'shing. "
        "Reading: order 1–13 (Part 1), 14–26 (Part 2), 27–40 (Part 3). Listening: order 1–10, 11–20, 21–30, 31–40 (Part 1–4). Writing: order 1 = Task 1, 2 = Task 2. Har bir savolda Part raqami maydonini to'ldiring."
    )
    show_change_link = True

    def get_fieldsets(self, request, obj=None):
        """MCQ va To'ldirish/Matching maydonlarini alohida fieldsetga — JS ularni savol turi bo'yicha yashiradi."""
        return [
            (None, {
                'fields': [
                    'order',
                    'variant',
                    'question_type',
                    'question_text',
                    'question_image',
                    # Admin ixtiyoriy ajratib turadigan UI presetlar (instruction/banner + prompt)
                    'instruction_box_style',
                    'prompt_text_style',
                ],
            }),
            ('Variantlar — faqat savol turi MCQ / True–False / T-F NG / Y-N NG bo\'lganda ko\'rinadi', {
                'fields': [
                    'max_choices', 'mcq_options_advanced',
                    ('option_a', 'option_b', 'option_c', 'option_d'),
                    ('option_e', 'option_f', 'option_g', 'option_h'),
                    'correct_answer',
                ],
                'classes': ['question-mcq-fields'],
                'description': (
                    '<strong>MCQ:</strong> Oddiy 4 variant: A–D. <strong>5–8 ta variant</strong> kerak bo‘lsa E–H ni ham to‘ldiring '
                    '(saytda a–h sifatida chiqadi). 9+ yoki maxsus harflar uchun «MCQ variantlar (ro‘yxat)» matn maydoni. '
                    '«Tanlash soni» 1 = bitta tanlov; 2 = ikkita harf (masalan a,c).'
                ),
            }),
            ("To'ldirish / Matching (Summary, Qisqa javob, Matching va b.)", {
                'fields': [
                    'part_number', 'instruction_text', 'fill_answers', 'writing_task_images', 'sa_prompt_lines',
                    'matching_items', 'matching_options', 'matching_correct',
                    'list_options_simple', 'list_correct_simple',
                ],
                'classes': ['question-fill-fields'],
                'description': (
                    "Part raqami: Reading 1–3, Listening 1–4, <strong>Writing 1 yoki 2</strong>. "
                    "<strong>Matching:</strong> 1) Savol matnini to'ldiring (draft bo'lmasin). 2) «Matching itemlar»: har qator <code>14|Paragraph A</code> yoki <code>14 The fact that...</code>. "
                    "3) «Matching variantlar»: <code>A|</code> yoki <code>a|Matn</code> (Information/Features). "
                    "<strong>Matching Headings</strong> uchun: <code>i|Sarlavha</code>, <code>ii|Boshqa</code> (rom raqam|matn). "
                    "4) «To'g'ri javob»: <code>14:ii</code> yoki <code>14: ii</code> (savol raqami:kichik harf/rom). "
                    "Barcha uchta blok to'ldirilguncha saqlash rad etilishi mumkin — xatolik matnini o'qing."
                ),
            }),
            (None, {
                'fields': ['points', 'explanation', 'audio_timestamp'],
            }),
        ]


class ReadingPassageForm(forms.ModelForm):
    """Passage matni uchun katta textarea."""
    class Meta:
        model = ReadingPassage
        fields = '__all__'
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': "Masalan: Passage 1 yoki Part 1"}),
            'text': forms.Textarea(attrs={'rows': 22, 'placeholder': "Bu yerga passage to'liq matnini yozing yoki PDF dan nusxalang..."}),
        }


class ReadingPassageInline(admin.StackedInline):
    model = ReadingPassage
    form = ReadingPassageForm
    extra = 0
    min_num = 0
    ordering = ['order']
    verbose_name = "Passage (o'qish matni)"
    verbose_name_plural = "📖 1-QADAM: Passage'lar — faqat Reading test uchun. 3 ta qo'shing (Order 1 = Part 1, 2 = Part 2, 3 = Part 3). 2 yoki 3 variantli testda har passage uchun Variant 1, 2 yoki 3 tanlang. Listening/Writing da bo'sh qoldiring."
    fields = ['order', 'variant', 'title', 'text']
    classes = []  # ochiq turishi uchun collapse yo'q


# Test Admin - ideal: partlar, savollar, testlar qo'shish oson
@admin.register(Test)
class TestAdmin(ImportExportModelAdmin):
    """Administrator test yaratadi/tahrirlaydi; saytda ko'rish uchun obyekt ustidagi «Saytda ko'rish»."""
    view_on_site = True  # Test.get_absolute_url → test tafsiloti

    list_display = [
        'title', 'category', 'test_type', 'variants_to_select', 'difficulty',
        'content_summary_display',
        'duration_minutes', 'passing_score', 'is_active', 'created_at'
    ]
    list_filter = ['category', 'test_type', 'difficulty', 'allow_retake', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-created_at']
    list_editable = ['is_active']
    list_per_page = 25
    inlines = [ReadingPassageInline, QuestionInline]
    autocomplete_fields = ['category']
    list_select_related = ['category']
    save_as = True
    save_on_top = True
    date_hierarchy = 'created_at'
    resource_class = TestResource

    actions = ['duplicate_tests', 'activate_tests', 'deactivate_tests', 'seed_ideal_tests']

    class Media:
        js = ('core/js/question_admin.js',)
        css = {'all': ('core/css/question_admin.css',)}

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('title', 'category', 'test_type', 'difficulty', 'variants_to_select', 'description', 'is_active'),
            'description': (
                "✅ <strong>1-qadam:</strong> maydonlarni to'ldirib <strong>Saqlash</strong> — keyin pastda Passage va Savollar paydo bo'ladi. "
                "<strong>Reading:</strong> 📖 Passage'lar (2–3 ta mumkin; har biri uchun Order 1,2,3) + 📝 savollar. "
                "Ko'p passage bo'lsa savolda <strong>Part raqami</strong> (1/2/3) yozing yoki tartibni saqlang — sayt passage soniga qarab partlarni bo'lib beradi. "
                "<strong>Listening:</strong> Audio fayl + savollar; Part 1–4 odatda 10+10+10+10. "
                "<strong>Writing:</strong> 2 ta savol (Task 1, 2) — har birida Part = 1 yoki 2; Task 1 rasmlari: «Rasm» yoki qo'shimcha URL ro'yxati. "
                "<strong>Savol matni bo'sh</strong> qoldirish mumkin (draft), keyin to'ldirib saqlang. "
                "<strong>2 yoki 3 variant</strong> testda har savol va passage uchun imtihon qog‘ozi varianti (1, 2 yoki 3) tanlang."
            )
        }),
        ('Parametrlar', {
            'fields': ('duration_minutes', 'passing_score', 'allow_retake', 'max_attempts'),
            'description': 'Davomiylik (daqiqa), o\'tish balli (%), qayta ishlash ruxsati.'
        }),
        ('Audio / Eski matn (ixtiyoriy)', {
            'fields': ('audio_file', 'reading_text'),
            'description': (
                "<strong>Listening:</strong> shu yerdan audio fayl (MP3) yuklang. "
                "<strong>Reading:</strong> afzal — pastdagi Passage inline; bu yerda faqat bitta zaxira matn (passage bo'lmasa ishlatiladi). Writing uchun kerak emas."
            )
        }),
        ('Tizim', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        # Har doim (add + change): auto_now / auto_now_add — formada faqat o'qiladi, aks holda add_view FieldError
        ro = list(super().get_readonly_fields(request, obj))
        ro.extend(['created_at', 'updated_at'])
        return ro

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['question_type_rules_json'] = question_type_rules_json()
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['question_type_rules_json'] = question_type_rules_json()
        return super().add_view(request, form_url, extra_context=extra_context)

    def content_summary_display(self, obj):
        """Ro'yxatda: 3 passage, 40 savol ko'rinishi."""
        p_count = obj.reading_passages.count() if hasattr(obj, 'reading_passages') else 0
        q_count = obj.questions.count() if hasattr(obj, 'questions') else 0
        if obj.test_type == 'reading' and p_count > 0:
            return format_html('<span title="Passage / Savol">{} p / {} s</span>', p_count, q_count)
        return format_html('<strong>{}</strong> savol', q_count)
    content_summary_display.short_description = "Passage / Savol"

    def total_questions_display(self, obj):
        count = obj.total_questions
        return format_html('<strong>{}</strong>', count)
    total_questions_display.short_description = "Savollar"

    def passages_display(self, obj):
        if obj.test_type != 'reading':
            return '—'
        n = obj.reading_passages.count()
        return format_html('<span title="Passage\'lar soni">{}</span>', n)
    passages_display.short_description = "Passage"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('reading_passages', 'questions')

    @admin.action(description="Testni nusxalash (passage + savollar bilan)")
    def duplicate_tests(self, request, queryset):
        n = 0
        for old in list(queryset):
            questions = list(old.questions.all().order_by('order', 'pk'))
            passages = list(old.reading_passages.all().order_by('order', 'pk'))
            with transaction.atomic():
                old.pk = None
                old._state.adding = True
                old.title = f"{old.title} (nusxa)"
                old.save()
                for p in passages:
                    p.pk = None
                    p.test = old
                    p._state.adding = True
                    p.save()
                for q in questions:
                    q.pk = None
                    q.test = old
                    q._state.adding = True
                    q.save()
            n += 1
        self.message_user(request, f"{n} ta test nusxalandi (har biri passage va savollar bilan).", messages.SUCCESS)

    @admin.action(description="Faollashtirish")
    def activate_tests(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} ta test faollashtirildi.")

    @admin.action(description="O'chirish (faol emas)")
    def deactivate_tests(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f"{n} ta test o'chirildi.")

    @admin.action(description="⚠️ DB ni tozalab ideal testlar (faqat superuser)")
    def seed_ideal_tests(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Bu harakat faqat superuser uchun. `python manage.py reset_and_seed` ni serverda ishlating.",
                level=messages.ERROR,
            )
            return
        try:
            call_command('reset_and_seed', verbosity=0)
            self.message_user(
                request,
                "reset_and_seed bajarildi: ideal testlar + namuna savollar.",
                level=messages.WARNING,
            )
        except Exception as e:
            self.message_user(request, f"Seeding xatolik: {e}", level=messages.ERROR)


# Question Admin - savol qo'shish qulay (yangi format: part/task ko'rsatish)
@admin.register(Question)
class QuestionAdmin(ImportExportModelAdmin):
    form = QuestionAdminForm
    list_display = ['test', 'order', 'part_or_task_display', 'question_type', 'question_text_short', 'correct_answer', 'points', 'created_at']
    list_filter = ['test__category', 'test__test_type', 'test__is_active', 'question_type', 'created_at']
    search_fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'test__title']
    ordering = ['test', 'order']
    list_per_page = 30
    autocomplete_fields = ['test']
    list_select_related = ['test', 'test__category']
    save_as = True
    save_on_top = True
    resource_class = QuestionResource

    def part_or_task_display(self, obj):
        opts = obj.options_json or {}
        part = opts.get('part')
        if part is not None:
            if obj.test and obj.test.test_type == 'writing':
                return f"Task {part}"
            return f"Part {part}"
        return '—'
    part_or_task_display.short_description = "Part / Task"

    fieldsets = (
        ('Asosiy', {
            'fields': (
                'test',
                'order',
                'question_type',
                'question_text',
                'question_image',
                'points',
                # Admin ixtiyoriy ajratib turadigan UI presetlar (instruction/banner + prompt)
                'instruction_box_style',
                'prompt_text_style',
            ),
            'description': (
                "Oddiy foydalanuvchi: JSON yozishingiz shart emas. Quyidagi oddiy maydonlarni to'ldiring — "
                "sistema avtomatik tarzda kerakli JSON ni yaratadi."
            )
        }),
        ('MCQ / True-False / Yes-No-Not Given', {
            'fields': (
                'max_choices', 'mcq_options_advanced',
                'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer',
            ),
            'classes': ('question-mcq-fields',),
            'description': (
                "<strong>MCQ moslashuvchan:</strong> «MCQ variantlar (ro'yxat)» — har satr harf|matn (3 ta, 5 ta variant). "
                "Bo'sh bo'lsa A–D. Tanlash 1 = bitta; 2 = ikki harf (a,e). "
                "True/False va boshqalar — avvalgidek."
            )
        }),
        ('Fill-in / Matching / List Selection — oddiy maydonlar (JSON emas)', {
            'fields': (
                'part_number',
                'instruction_text',
                'fill_answers',
                'writing_task_images',
                'matching_items',
                'matching_options',
                'matching_correct',
                'list_options_simple',
                'list_correct_simple',
            ),
            'classes': ('question-fill-fields',),
            'description': (
                "Bu maydonlarni to'ldirsangiz, JSON avtomatik yoziladi. Notes/Summary: savol matnida [1], [2], [3] yozing; "
                "To'g'ri javoblar: vergul bilan. "
                "<strong>Reading 2–3 ta passage</strong> bo'lsa, har bir savol uchun «Part raqami» ni 1, 2 yoki 3 qilib belgilang — "
                "aks holda tizim savollarni passage tartibiga bo'lib beradi. "
                "Matching uchun yuqoridagi inline yo'riqnomani o'qing."
            )
        }),
        ('Advanced JSON (faqat mutaxassis — odatda kerak emas)', {
            'fields': ('correct_answer_json', 'options_json'),
            'classes': ('collapse',),
            'description': (
                "Oddiy foydalanuvchi bu blokni ochmasin. Yuqoridagi oddiy maydonlar yetarli. "
                "Faqat maxsus holatlar (masalan, Writing da bir nechta rasm) uchun ishlatiladi."
            )
        }),
        ('Tushuntirish va Listening', {
            'fields': ('explanation', 'audio_timestamp')
        }),
    )

    class Media:
        js = ('core/js/question_admin.js',)
        css = {'all': ('core/css/question_admin.css',)}

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['question_type_rules_json'] = question_type_rules_json()
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['question_type_rules_json'] = question_type_rules_json()
        return super().add_view(request, form_url, extra_context=extra_context)

    def question_text_short(self, obj):
        t = obj.question_text or ''
        return (t[:80] + '...') if len(t) > 80 else t
    question_text_short.short_description = "Savol"
