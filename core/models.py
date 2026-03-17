from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
import re


class Category(models.Model):
    """Kategoriya modeli"""
    name = models.CharField(max_length=200, verbose_name="Nomi")
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Ota kategoriya",
    )
    description = models.TextField(blank=True, verbose_name="Tavsif")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Icon (Font Awesome)")
    color = models.CharField(max_length=7, default="#007bff", verbose_name="Rang (hex)")
    order = models.IntegerField(default=0, verbose_name="Tartib")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    show_on_site = models.BooleanField(
        default=True,
        verbose_name="Interfeysda ko'rsatish",
        help_text="O'chirilsa — faqat admin panelda ko'rinadi, foydalanuvchi sahifasida emas."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=['parent', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('core:category_detail', kwargs={'slug': self.slug})


class VideoLesson(models.Model):
    """Video dars modeli. Video fayl yuklangan bo'lsa u ko'rsatiladi, aks holda YouTube URL ishlatiladi."""
    title = models.CharField(max_length=300, verbose_name="Sarlavha")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='videos', verbose_name="Kategoriya")
    video_file = models.FileField(
        upload_to='videos/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Video fayl",
        help_text="Admin orqali yuklangan video. Bo'lsa, interfeysda shu video ko'rsatiladi."
    )
    youtube_url = models.URLField(blank=True, null=True, verbose_name="YouTube URL (ixtiyoriy)")
    youtube_id = models.CharField(max_length=50, blank=True, db_index=True, verbose_name="YouTube ID")
    youtube_thumbnail = models.URLField(blank=True, verbose_name="Thumbnail URL")
    cover_image = models.ImageField(
        upload_to='video_covers/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Obloshka (cover)",
        help_text="Video kartochkasida ko'rinadigan rasm. Yuklanmasa, YouTube thumbnail yoki placeholder ishlatiladi."
    )
    description = models.TextField(blank=True, verbose_name="Tavsif")
    duration = models.IntegerField(default=0, verbose_name="Davomiyligi (soniya)")
    order = models.IntegerField(default=0, verbose_name="Tartib")
    views_count = models.IntegerField(default=0, verbose_name="Ko'rilganlar soni")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def average_rating(self):
        """O'rtacha reyting"""
        from django.db.models import Avg
        rating = self.ratings.aggregate(Avg('rating'))['rating__avg']
        return round(rating, 1) if rating else 0
    
    @property
    def total_ratings(self):
        """Jami reytinglar soni"""
        return self.ratings.count()

    class Meta:
        verbose_name = "Video Dars"
        verbose_name_plural = "Video Darslar"
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['youtube_id']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """YouTube URL dan ID ni ajratib olish"""
        if self.youtube_url:
            # Har doim youtube_id ni yangilash
            extracted_id = self.extract_youtube_id(self.youtube_url)
            if extracted_id and len(extracted_id) == 11:
                # Faqat to'g'ri ID bo'lsa saqlash
                self.youtube_id = extracted_id
                if not self.youtube_thumbnail:
                    self.youtube_thumbnail = f"https://img.youtube.com/vi/{self.youtube_id}/maxresdefault.jpg"
            else:
                # Agar ID extract qilinmasa yoki noto'g'ri bo'lsa, youtube_id ni tozalash
                self.youtube_id = ''
        super().save(*args, **kwargs)

    @staticmethod
    def extract_youtube_id(url):
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

    def get_embed_url(self, use_nocookie=True):
        """
        Get YouTube embed URL.
        
        Args:
            use_nocookie: If True, use youtube-nocookie.com (privacy-enhanced mode)
        
        Returns:
            Embed URL string or None if video ID cannot be determined
        """
        video_id = None
        
        if self.youtube_id and len(self.youtube_id) == 11:
            video_id = self.youtube_id
        elif self.youtube_url:
            # Extract from URL if youtube_id is missing
            extracted_id = self.extract_youtube_id(self.youtube_url)
            if extracted_id and len(extracted_id) == 11:
                video_id = extracted_id
                # Cache it
                if not self.youtube_id:
                    self.youtube_id = extracted_id
                    self.save(update_fields=['youtube_id'])
        
        if video_id:
            if use_nocookie:
                return f"https://www.youtube-nocookie.com/embed/{video_id}"
            return f"https://www.youtube.com/embed/{video_id}"
        
        return None

    def get_absolute_url(self):
        return reverse('core:video_detail', kwargs={'pk': self.pk})


class Test(models.Model):
    """Test modeli"""
    TEST_TYPES = [
        ('reading', 'Reading'),
        ('writing', 'Writing'),
        ('listening', 'Listening'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('easy', 'Oson'),
        ('medium', 'O\'rta'),
        ('hard', 'Qiyin'),
    ]

    title = models.CharField(max_length=300, verbose_name="Sarlavha")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='tests', verbose_name="Kategoriya")
    test_type = models.CharField(max_length=20, choices=TEST_TYPES, verbose_name="Test turi")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='medium', verbose_name="Qiyinlik darajasi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    duration_minutes = models.IntegerField(null=True, blank=True, verbose_name="Davomiyligi (daqiqa)")
    passing_score = models.IntegerField(default=60, verbose_name="O'tish balli (%)")
    allow_retake = models.BooleanField(default=True, verbose_name="Qayta ishlashga ruxsat")
    max_attempts = models.IntegerField(null=True, blank=True, verbose_name="Maksimal urinishlar soni (bo'sh bo'lsa cheksiz)")
    # Listening testlar uchun audio fayl
    audio_file = models.FileField(upload_to='test_audio/', blank=True, null=True, verbose_name="Audio fayl (Listening)")
    # Reading testlar uchun matn
    reading_text = models.TextField(blank=True, verbose_name="O'qish matni (Reading)")
    # Reading: 3 ta passage [{"title": "...", "text": "..."}, ...]. Bo'sh bo'lsa reading_text ishlatiladi
    reading_passages_json = models.JSONField(default=list, blank=True, verbose_name="Passage'lar (3 ta)")
    # 1 yoki 2 variantli test: 2 bo'lsa har bir savol/passage da variant (1 yoki 2) belgilash kerak
    variants_to_select = models.PositiveSmallIntegerField(
        default=1,
        choices=[(1, "1 variant"), (2, "2 variant")],
        verbose_name="Variantlar soni",
        help_text="2 qilsangiz — foydalanuvchi ikkala variantni ham bajaradi; har bir savol va passage da «Variant 1» yoki «Variant 2» tanlang.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'test_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_test_type_display()})"

    @property
    def total_questions(self):
        """Jami savollar soni"""
        return self.questions.count()

    def get_absolute_url(self):
        return reverse('core:test_detail', kwargs={'pk': self.pk})

    def get_reading_passages(self):
        """Reading: passage'lar ro'yxati. 2 variantli testda [v1_list, v2_list], aks holda bitta ro'yxat."""
        # 1) Inline model (eng qulay)
        objs = list(self.reading_passages.all().order_by('variant', 'order'))
        if objs:
            if self.variants_to_select == 2:
                v1 = [{'title': p.title or f'Passage {i+1}', 'text': p.text or ''} for i, p in enumerate([x for x in objs if (x.variant or 1) == 1])]
                v2 = [{'title': p.title or f'Passage {i+1}', 'text': p.text or ''} for i, p in enumerate([x for x in objs if x.variant == 2])]
                return [v1, v2]
            return [{'title': p.title or f'Passage {i+1}', 'text': p.text or ''} for i, p in enumerate(objs)]
        # 2) JSON (eski format)
        passages = self.reading_passages_json or []
        if passages and isinstance(passages, list) and len(passages) > 0:
            if self.variants_to_select == 2:
                return [passages[: len(passages) // 2], passages[len(passages) // 2 :]] if len(passages) >= 2 else [passages, []]
            return [{'title': p.get('title', f'Passage {i+1}'), 'text': p.get('text', '')} for i, p in enumerate(passages) if isinstance(p, dict)]
        # 3) Bitta matn
        if self.reading_text:
            return [{'title': 'Passage 1', 'text': self.reading_text}]
        return []


class ReadingPassage(models.Model):
    """Reading test uchun passage - Test inline orqali boshqariladi."""
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='reading_passages', verbose_name="Test")
    order = models.PositiveIntegerField(default=1, verbose_name="Tartib")
    title = models.CharField(max_length=255, blank=True, verbose_name="Sarlavha (masalan: Passage 1)")
    text = models.TextField(blank=True, verbose_name="Matn")
    variant = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(1, "Variant 1"), (2, "Variant 2")],
        verbose_name="Variant (2 variantli testda)",
        help_text="Faqat test «2 variant» bo'lsa to'ldiring.",
    )

    class Meta:
        ordering = ['test', 'order']
        verbose_name = "Passage"
        verbose_name_plural = "Passage'lar"

    def __str__(self):
        return self.title or f"Passage {self.order}"


class Question(models.Model):
    """Savol modeli - IELTS barcha savol turlari"""
    QUESTION_TYPES = [
        # Asosiy tanlov
        ('mcq', 'Multiple Choice (A/B/C/D)'),
        ('true_false', 'True / False'),
        ('true_false_not_given', 'True / False / Not Given (Reading)'),
        ('yes_no_not_given', 'Yes / No / Not Given'),
        # To'ldirish turlari
        ('fill_blank', "Bo'sh joyni to'ldirish (bitta so'z)"),
        ('summary_completion', 'Summary Completion (Reading)'),
        ('notes_completion', 'Notes Completion (Listening)'),
        ('sentence_completion', 'Sentence Completion'),
        ('table_completion', 'Table Completion'),
        ('short_answer', "Qisqa javob"),
        ('essay', 'Essay (Writing Task)'),
        # Moslashtirish turlari
        ('matching_headings', 'Matching Headings (matnga sarlavha)'),
        ('matching_sentences', 'Matching Sentence Endings'),
        ('matching_features', 'Matching Features (elementlarni toifalarga)'),
        ('matching_info', 'Matching Information (paragraflarga)'),
        # Boshqa
        ('classification', 'Classification (A/B/C ga tasniflash)'),
        ('list_selection', 'List Selection (ro\'yxatdan tanlash)'),
    ]
    
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions', verbose_name="Test")
    variant = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(1, "Variant 1"), (2, "Variant 2")],
        verbose_name="Variant (2 variantli testda)",
        help_text="Faqat test «2 variant» bo'lsa tanlang.",
    )
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPES, default='mcq', verbose_name="Savol turi")
    question_text = models.TextField(verbose_name="Savol matni")
    question_image = models.ImageField(upload_to='questions/', blank=True, null=True, verbose_name="Rasm")
    # Listening testlar uchun audio timestamp (qaysi vaqtda audio eshitilishi kerak)
    audio_timestamp = models.FloatField(null=True, blank=True, verbose_name="Audio vaqti (soniya) - Listening")
    # MCQ uchun variantlar (question_type='mcq' yoki 'true_false' bo'lsa)
    option_a = models.CharField(max_length=500, blank=True, verbose_name="Variant A")
    option_b = models.CharField(max_length=500, blank=True, verbose_name="Variant B")
    option_c = models.CharField(max_length=500, blank=True, verbose_name="Variant C")
    option_d = models.CharField(max_length=500, blank=True, verbose_name="Variant D")
    correct_answer = models.CharField(max_length=10, blank=True, verbose_name="To'g'ri javob (MCQ: a/b/c/d)")
    # MCQ/True-False da: 1 = bitta variant tanlash (radio), 2 = ikkita variant tanlash (checkbox)
    max_choices = models.PositiveSmallIntegerField(
        default=1,
        choices=[(1, "1 ta javob"), (2, "2 ta javob")],
        verbose_name="Tanlash soni (MCQ/T-F)",
        help_text="«2 ta javob» qilsangiz — foydalanuvchi ikkita variantni belgilaydi; to'g'ri javobda ikkalasini kiriting (masalan a,c).",
    )
    # G'arbiy savol turlari uchun - JSON formatda
    # options_json: {"instruction": "ONE WORD ONLY", "blanks_count": 4}
    options_json = models.JSONField(default=dict, blank=True, verbose_name="Qo'shimcha parametrlar (JSON)")
    # correct_answer_json: ["jackals", "diseases", "food", "foxes"] - fill_blank/summary/notes uchun
    correct_answer_json = models.JSONField(default=list, blank=True, verbose_name="To'g'ri javoblar ro'yxati (JSON)")
    explanation = models.TextField(blank=True, verbose_name="Tushuntirish")
    points = models.IntegerField(default=1, verbose_name="Ball")
    order = models.IntegerField(default=0, verbose_name="Tartib")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['test', 'order']),
        ]

    def __str__(self):
        return f"{self.test.title} - Savol #{self.order}"

    @property
    def question_instruction(self):
        """Ko'rsatma matni (options_json.instruction)"""
        opts = self.options_json or {}
        return opts.get('instruction', '')

    def get_task_images(self, request=None):
        """Writing task uchun rasmlar ro'yxati (carousel). question_image + options_json.images"""
        from django.conf import settings
        urls = []
        if self.question_image:
            url = self.question_image.url
            if request and not url.startswith(('http://', 'https://')):
                url = request.build_absolute_uri(url)
            urls.append(url)
        for item in (self.options_json or {}).get('images', []):
            path = item if isinstance(item, str) else (item.get('path') or item.get('url', ''))
            if path:
                base = (settings.MEDIA_URL or '/media/').rstrip('/') + '/'
                full = base + path.lstrip('/') if not path.startswith(('http', '/')) else path
                if request and not full.startswith(('http://', 'https://')):
                    full = request.build_absolute_uri(full)
                urls.append(full)
        return urls

    def get_user_answer_display(self, user_answer):
        """Foydalanuvchi javobini ko'rsatish"""
        single_choice = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
        if self.question_type in single_choice:
            opts = {'a': self.option_a, 'b': self.option_b, 'c': self.option_c, 'd': self.option_d}
            if getattr(self, 'max_choices', 1) == 2 and user_answer:
                try:
                    import json
                    raw = user_answer if isinstance(user_answer, str) else str(user_answer)
                    if raw.strip().startswith('['):
                        letters = json.loads(raw)
                        letters = letters if isinstance(letters, list) else [letters]
                        parts = [f"{str(l).upper()}) {opts.get(str(l).lower(), '')}" for l in letters if str(l).lower() in opts]
                        return '; '.join(parts) if parts else raw
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
            return opts.get(str(user_answer).lower(), user_answer)
        return str(user_answer) if user_answer else ''

    def get_correct_answer_display_for_review(self):
        """Natija sahifasida to'g'ri javob matni: bitta yoki 2 ta variant (A) Matn; C) Matn)."""
        single_choice = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
        if self.question_type not in single_choice:
            return ''
        opts = {'a': self.option_a, 'b': self.option_b, 'c': self.option_c, 'd': self.option_d}
        if getattr(self, 'max_choices', 1) == 2 and self.correct_answer_json and isinstance(self.correct_answer_json, list) and len(self.correct_answer_json) >= 2:
            parts = [f"{str(l).upper()}) {opts.get(str(l).lower(), '')}" for l in self.correct_answer_json[:2]]
            return '; '.join(parts)
        letter = str(self.correct_answer).strip().lower() if self.correct_answer else ''
        text = opts.get(letter, '')
        return f"{letter.upper()}) {text}" if letter else text

    def get_correct_answers_list(self):
        """To'g'ri javoblarni ro'yxat sifatida olish"""
        if self.correct_answer_json:
            return self.correct_answer_json
        if self.correct_answer:
            return [self.correct_answer]
        return []
    
    def check_user_answer(self, user_answer):
        """Foydalanuvchi javobi to'g'rimi tekshirish"""
        import json
        if self.question_type == 'essay':
            #mmm
            # Essay avtomatik baholanmaydi – faqat bo'sh emasligi tekshiriladi
            return False
        single_choice = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
        if self.question_type in single_choice:
            norm = lambda x: str(x).strip().lower() if x else ''
            # 2 ta javob tanlash: user_answer JSON ro'yxat ["a","c"], to'g'ri javob correct_answer_json yoki correct_answer
            if getattr(self, 'max_choices', 1) == 2:
                try:
                    ua = user_answer if isinstance(user_answer, list) else (json.loads(user_answer) if isinstance(user_answer, str) and user_answer.strip().startswith('[') else [user_answer])
                    u_set = set(norm(x) for x in (ua if isinstance(ua, list) else [ua]))
                    correct_list = self.correct_answer_json if isinstance(self.correct_answer_json, list) and len(self.correct_answer_json) >= 2 else [self.correct_answer]
                    c_set = set(norm(x) for x in correct_list)
                    return u_set == c_set
                except (TypeError, json.JSONDecodeError):
                    return False
            return norm(user_answer) == norm(self.correct_answer)
        
        fill_types = ('fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion',
                      'table_completion', 'short_answer')
        matching_types = ('matching_headings', 'matching_features', 'matching_info', 'matching_sentences', 'classification')
        
        import json
        norm = lambda x: (str(x).strip().lower() if x else '')
        
        def parse_user_json(text):
            if not text:
                return [] if self.question_type in fill_types else {}
            t = str(text).strip()
            if t.startswith('[') or t.startswith('{'):
                try:
                    return json.loads(t)
                except json.JSONDecodeError:
                    return [t] if self.question_type in fill_types else {}
            return [t]
        
        # Matching (dict format: {"1":"ii", "2":"v"})
        if self.question_type in matching_types:
            correct = self.correct_answer_json if isinstance(self.correct_answer_json, dict) else {}
            user_data = parse_user_json(user_answer)
            if not isinstance(user_data, dict):
                return False
            if set(user_data.keys()) != set(str(k) for k in correct.keys()):
                return False
            return all(norm(user_data.get(str(k), '')) == norm(v) for k, v in correct.items())
        
        # List selection - order doesn't matter, check if same set
        if self.question_type == 'list_selection':
            correct = set(norm(x) for x in (self.correct_answer_json or []))
            user_data = parse_user_json(user_answer)
            user_set = set(norm(x) for x in (user_data if isinstance(user_data, list) else [user_data]))
            return correct == user_set
        
        # Fill-in types (list format). Bitta yacheykada 2 ta so'z: to'g'ri javob "word1 word2" bo'lsa, foydalanuvchi ikkalasini ham yozishi kerak (tartibi muhim emas)
        correct_list = self.get_correct_answers_list()
        if not correct_list:
            return False
        user_answers = parse_user_json(user_answer)
        if isinstance(user_answers, dict):
            user_answers = [user_answers.get(str(i+1), '') for i in range(len(correct_list))]
        elif not isinstance(user_answers, list):
            user_answers = [user_answers]
        if len(user_answers) != len(correct_list):
            return False
        def blank_match(ua, ca):
            ua_n = norm(ua)
            ca_n = norm(ca)
            if not ca_n:
                return not ua_n
            if ' ' in ca_n or ' ' in ua_n:
                ca_words = set(w for w in ca_n.split() if w)
                ua_words = set(w for w in ua_n.split() if w)
                return ca_words == ua_words
            return ua_n == ca_n
        return all(blank_match(ua, ca) for ua, ca in zip(user_answers, correct_list))


class QuestionTypeRule(models.Model):
    """
    Har bir savol TURI uchun bitta shart (qoida/talab).
    Savol qo'shishda tanlangan tur uchun shu shart ko'rsatiladi — har bir savolga emas, faqat tur bo'yicha.
    """
    question_type = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Savol turi",
        help_text="Question.QUESTION_TYPES dagi qiymat (mcq, true_false, fill_blank, ...)"
    )
    name_uz = models.CharField(max_length=200, verbose_name="Nomi (o'zbekcha)")
    shart_text = models.TextField(
        blank=True,
        verbose_name="Shart (qoida / talab)",
        help_text="Bu savol turi uchun talab matni. Admin da savol qo'shishda tanlangan turda shu matn ko'rsatiladi."
    )
    order = models.IntegerField(default=0, verbose_name="Tartib")

    class Meta:
        verbose_name = "Savol turi qoidasi"
        verbose_name_plural = "Savol turi qoidalari"
        ordering = ['order', 'question_type']

    def __str__(self):
        return f"{self.name_uz} ({self.question_type})"


class UserTestResult(models.Model):
    """Foydalanuvchi test natijasi"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results', verbose_name="Foydalanuvchi")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='results', verbose_name="Test")
    score = models.IntegerField(default=0, verbose_name="Ball")
    total_questions = models.IntegerField(default=0, verbose_name="Jami savollar")
    percentage = models.FloatField(default=0.0, verbose_name="Foiz")
    correct_answers = models.IntegerField(default=0, verbose_name="To'g'ri javoblar")
    wrong_answers = models.IntegerField(default=0, verbose_name="Noto'g'ri javoblar")
    time_taken = models.IntegerField(default=0, verbose_name="Sarflangan vaqt (soniya)")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan vaqt")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Yakunlangan vaqt")
    answers_json = models.JSONField(default=dict, verbose_name="Javoblar (JSON)")
    attempt_number = models.IntegerField(default=1, verbose_name="Urinish raqami")
    # Pause/Resume funksiyalari uchun
    is_paused = models.BooleanField(default=False, verbose_name="To'xtatilgan")
    paused_at = models.DateTimeField(null=True, blank=True, verbose_name="To'xtatilgan vaqt")
    paused_duration = models.IntegerField(default=0, verbose_name="To'xtatilgan vaqt (soniya)")
    # Timer uchun
    timer_started_at = models.DateTimeField(null=True, blank=True, verbose_name="Timer boshlangan vaqt")
    timer_seconds_left = models.IntegerField(null=True, blank=True, verbose_name="Timer qolgan vaqt (soniya)")

    class Meta:
        verbose_name = "Test Natijasi"
        verbose_name_plural = "Test Natijalari"
        ordering = ['-completed_at', '-started_at']
        indexes = [
            models.Index(fields=['user', 'test']),
            models.Index(fields=['user', '-completed_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.test.title} ({self.percentage}%)"

    def calculate_score(self):
        """Natijani hisoblash"""
        # Agar total_questions 0 bo'lsa, test.questions.count() dan olish
        if self.total_questions == 0:
            self.total_questions = self.test.total_questions if self.test else 0
        
        total = self.total_questions
        if total == 0:
            self.percentage = 0.0
            self.score = 0
            self.save()
            return
        
        correct = self.correct_answers
        self.score = correct
        self.percentage = round((correct / total) * 100, 2)
        self.wrong_answers = total - correct
        self.save()

    def recalculate_from_answers(self):
        """Javoblar asosida correct/wrong ni qayta hisoblash (admin baholagach chaqiriladi)"""
        self.correct_answers = self.answers.filter(is_correct=True).count()
        gradable = self.answers.exclude(question__question_type='essay')
        self.wrong_answers = gradable.filter(is_correct=False).count()
        total = self.total_questions or (self.test.total_questions if self.test else 0)
        self.score = self.correct_answers
        self.percentage = round((self.correct_answers / total) * 100, 2) if total else 0.0
        self.save()

    def is_passed(self):
        """Test o'tildimi?"""
        return self.percentage >= self.test.passing_score
    
    def pause_test(self):
        """Testni to'xtatish"""
        if not self.is_paused:
            self.is_paused = True
            self.paused_at = timezone.now()
            self.save()
    
    def resume_test(self):
        """Testni davom ettirish"""
        if self.is_paused and self.paused_at:
            pause_duration = (timezone.now() - self.paused_at).total_seconds()
            self.paused_duration += int(pause_duration)
            self.is_paused = False
            self.paused_at = None
            self.save()
    
    def get_elapsed_time(self):
        """Sarflangan vaqtni hisoblash (to'xtatilgan vaqtni hisobga olgan holda)"""
        if self.completed_at:
            total_duration = (self.completed_at - self.started_at).total_seconds()
            return int(total_duration) - self.paused_duration
        elif self.is_paused and self.paused_at:
            # Hozir to'xtatilgan
            elapsed = (self.paused_at - self.started_at).total_seconds()
            return int(elapsed) - self.paused_duration
        else:
            # Hozir ishlanmoqda
            elapsed = (timezone.now() - self.started_at).total_seconds()
            return int(elapsed) - self.paused_duration
    
    def get_timer_seconds_left(self):
        """Timer qolgan vaqtni hisoblash"""
        if not self.test.duration_minutes:
            return None
        
        total_seconds = self.test.duration_minutes * 60
        elapsed = self.get_elapsed_time()
        remaining = total_seconds - elapsed
        
        return max(0, int(remaining))


class UserTestAnswer(models.Model):
    """Har bir savol uchun foydalanuvchi javobi"""
    test_result = models.ForeignKey(UserTestResult, on_delete=models.CASCADE, related_name='answers', verbose_name="Test natijasi")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Savol")
    # MCQ: "a","b","c","d" | Fill-in: "word" yoki JSON ["w1","w2",...]
    user_answer = models.TextField(blank=True, verbose_name="Foydalanuvchi javobi")
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri")
    answered_at = models.DateTimeField(auto_now_add=True, verbose_name="Javob berilgan vaqt")

    class Meta:
        verbose_name = "Test Javobi"
        verbose_name_plural = "Test Javoblari"
        ordering = ['test_result', 'question__order']
        indexes = [
            models.Index(fields=['test_result', 'question']),
        ]

    def __str__(self):
        return f"{self.test_result.user.username} - {self.question} - {self.user_answer}"

    def check_answer(self):
        """Javobni tekshirish — savol turiga qarab Question.check_user_answer ishlatiladi."""
        self.is_correct = self.question.check_user_answer(self.user_answer)
        self.save(update_fields=['is_correct'])
        return self.is_correct


class UserVideoProgress(models.Model):
    """Foydalanuvchi video progress"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_progress', verbose_name="Foydalanuvchi")
    video = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, related_name='progress', verbose_name="Video")
    watched = models.BooleanField(default=False, verbose_name="Ko'rilgan")
    watch_percentage = models.IntegerField(default=0, verbose_name="Foiz (0-100)")
    last_watched_at = models.DateTimeField(auto_now=True, verbose_name="Oxirgi ko'rilgan vaqt")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Yakunlangan vaqt")

    class Meta:
        verbose_name = "Video Progress"
        verbose_name_plural = "Video Progresslar"
        unique_together = ['user', 'video']
        ordering = ['-last_watched_at']
        indexes = [
            models.Index(fields=['user', 'video']),
            models.Index(fields=['user', 'watched']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.video.title} ({self.watch_percentage}%)"

    def mark_as_watched(self):
        """Video ko'rilgan deb belgilash"""
        self.watched = True
        self.watch_percentage = 100
        if not self.completed_at:
            self.completed_at = timezone.now()
        self.save()

    def update_progress(self, percentage):
        """Progress yangilash"""
        self.watch_percentage = min(100, max(0, percentage))
        if self.watch_percentage >= 90:
            self.watched = True
            if not self.completed_at:
                self.completed_at = timezone.now()
        self.save()


class UserActivity(models.Model):
    """Foydalanuvchi faolligi"""
    ACTIVITY_TYPES = [
        ('login', 'Kirish'),
        ('test_start', 'Test boshlash'),
        ('test_complete', 'Test yakunlash'),
        ('video_watch', 'Video ko\'rish'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities', verbose_name="Foydalanuvchi")
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES, verbose_name="Faollik turi")
    related_object_id = models.IntegerField(null=True, blank=True, verbose_name="Bog'liq obyekt ID")
    related_object_type = models.CharField(max_length=50, blank=True, verbose_name="Bog'liq obyekt turi")
    metadata = models.JSONField(default=dict, verbose_name="Qo'shimcha ma'lumotlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Vaqt")

    class Meta:
        verbose_name = "Faollik"
        verbose_name_plural = "Faolliklar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'activity_type', '-created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()} - {self.created_at}"


class Bookmark(models.Model):
    """Sevimli videolar va testlar"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks', verbose_name="Foydalanuvchi")
    video = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, null=True, blank=True, related_name='bookmarks', verbose_name="Video")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True, related_name='bookmarks', verbose_name="Test")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Bookmark"
        verbose_name_plural = "Bookmarks"
        unique_together = [
            ['user', 'video'],
            ['user', 'test'],
        ]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'video']),
            models.Index(fields=['user', 'test']),
        ]

    def __str__(self):
        if self.video:
            return f"{self.user.username} - {self.video.title}"
        return f"{self.user.username} - {self.test.title}"
    
    def save(self, *args, **kwargs):
        # Validation
        if not self.video and not self.test:
            raise ValueError("Video yoki Test tanlanishi kerak")
        if self.video and self.test:
            raise ValueError("Faqat Video yoki Test tanlanishi kerak")
        super().save(*args, **kwargs)


class StudyStreak(models.Model):
    """Kunlik faollik streak"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='streaks', verbose_name="Foydalanuvchi")
    date = models.DateField(verbose_name="Sana")
    activities_count = models.IntegerField(default=0, verbose_name="Faolliklar soni")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Study Streak"
        verbose_name_plural = "Study Streaks"
        unique_together = ['user', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', '-date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.activities_count})"

    @staticmethod
    def get_current_streak(user):
        """Joriy streak ni olish"""
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        streak = 0
        current_date = today
        
        while True:
            day_streak = StudyStreak.objects.filter(user=user, date=current_date).first()
            if day_streak and day_streak.activities_count > 0:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        return streak

    @staticmethod
    def update_streak(user):
        """Streak yangilash"""
        from django.utils import timezone
        today = timezone.now().date()
        streak, created = StudyStreak.objects.get_or_create(
            user=user,
            date=today,
            defaults={'activities_count': 1}
        )
        if not created:
            streak.activities_count += 1
            streak.save()
        return streak


class VideoNote(models.Model):
    """Video eslatmalar"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_notes', verbose_name="Foydalanuvchi")
    video = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, related_name='notes', verbose_name="Video")
    note_text = models.TextField(verbose_name="Eslatma matni")
    timestamp = models.IntegerField(default=0, verbose_name="Vaqt (soniya)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Video Eslatma"
        verbose_name_plural = "Video Eslatmalar"
        ordering = ['timestamp', 'created_at']
        indexes = [
            models.Index(fields=['user', 'video']),
            models.Index(fields=['video', 'timestamp']),
        ]

    def __str__(self):
        minutes = self.timestamp // 60
        seconds = self.timestamp % 60
        return f"{self.user.username} - {self.video.title} ({minutes}:{seconds:02d})"
    
    def get_timestamp_display(self):
        """Vaqtni ko'rsatish formatida"""
        minutes = self.timestamp // 60
        seconds = self.timestamp % 60
        return f"{minutes}:{seconds:02d}"


class VideoRating(models.Model):
    """Video reyting"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_ratings', verbose_name="Foydalanuvchi")
    video = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, related_name='ratings', verbose_name="Video")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name="Reyting (1-5)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Video Reyting"
        verbose_name_plural = "Video Reytinglar"
        unique_together = ['user', 'video']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'video']),
            models.Index(fields=['video', 'rating']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.video.title} ({self.rating}/5)"


class VideoComment(models.Model):
    """Video izohlar"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_comments', verbose_name="Foydalanuvchi")
    video = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, related_name='comments', verbose_name="Video")
    comment_text = models.TextField(verbose_name="Izoh matni")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', verbose_name="Javob")
    is_edited = models.BooleanField(default=False, verbose_name="Tahrirlangan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Video Izoh"
        verbose_name_plural = "Video Izohlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['video', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.video.title[:50]}"

    @property
    def replies_count(self):
        """Javoblar soni"""
        return self.replies.count()


class VideoPlaylist(models.Model):
    """Video playlist"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_playlists', verbose_name="Foydalanuvchi")
    name = models.CharField(max_length=200, verbose_name="Playlist nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    is_public = models.BooleanField(default=False, verbose_name="Ochiq")
    videos = models.ManyToManyField(VideoLesson, through='PlaylistVideo', related_name='playlists', verbose_name="Videolar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Video Playlist"
        verbose_name_plural = "Video Playlistlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_public']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    @property
    def videos_count(self):
        """Videolar soni"""
        return self.videos.count()


class PlaylistVideo(models.Model):
    """Playlist va video orasidagi bog'lanish"""
    playlist = models.ForeignKey(VideoPlaylist, on_delete=models.CASCADE, related_name='playlist_videos', verbose_name="Playlist")
    video = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, related_name='playlist_videos', verbose_name="Video")
    order = models.IntegerField(default=0, verbose_name="Tartib")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan vaqt")

    class Meta:
        verbose_name = "Playlist Video"
        verbose_name_plural = "Playlist Videolar"
        unique_together = ['playlist', 'video']
        ordering = ['order', 'added_at']
        indexes = [
            models.Index(fields=['playlist', 'order']),
        ]

    def __str__(self):
        return f"{self.playlist.name} - {self.video.title}"


class FlashcardSet(models.Model):
    """Foydalanuvchi flashcard to'plami."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcard_sets', verbose_name="Foydalanuvchi")
    name = models.CharField(max_length=120, verbose_name="Set nomi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Flashcard Set"
        verbose_name_plural = "Flashcard Setlar"
        ordering = ['name', '-created_at']
        unique_together = ['user', 'name']
        indexes = [
            models.Index(fields=['user', 'name']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Flashcard(models.Model):
    """Test/reading matnidan saqlanadigan flashcard."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards', verbose_name="Foydalanuvchi")
    flashcard_set = models.ForeignKey(FlashcardSet, on_delete=models.CASCADE, related_name='cards', verbose_name="Set")
    term = models.CharField(max_length=255, verbose_name="Term")
    definition = models.TextField(blank=True, verbose_name="Definition")
    source_test = models.ForeignKey(Test, on_delete=models.SET_NULL, null=True, blank=True, related_name='flashcards', verbose_name="Manba test")
    source_question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True, related_name='flashcards', verbose_name="Manba savol")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Flashcard"
        verbose_name_plural = "Flashcardlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['flashcard_set']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.term[:50]}"


# Signal: UserTestAnswer o'zgarganda natijani qayta hisoblash (admin essay baholaganda)
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=UserTestAnswer)
def recalc_result_on_answer_save(sender, instance, created, **kwargs):
    """UserTestAnswerAdmin orqali is_correct o'zgartirilganda natijani yangilash"""
    if created:
        return  # finish_test da view o'zi hisoblaydi
    if instance.test_result_id:
        instance.test_result.recalculate_from_answers()
