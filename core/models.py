from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
import re


class Category(models.Model):
    """Kategoriya modeli"""
    name = models.CharField(max_length=200, verbose_name="Nomi")
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True, verbose_name="Tavsif")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Icon (Font Awesome)")
    color = models.CharField(max_length=7, default="#007bff", verbose_name="Rang (hex)")
    order = models.IntegerField(default=0, verbose_name="Tartib")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('core:category_detail', kwargs={'slug': self.slug})


class VideoLesson(models.Model):
    """Video dars modeli"""
    title = models.CharField(max_length=300, verbose_name="Sarlavha")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='videos', verbose_name="Kategoriya")
    youtube_url = models.URLField(verbose_name="YouTube URL")
    youtube_id = models.CharField(max_length=50, blank=True, db_index=True, verbose_name="YouTube ID")
    youtube_thumbnail = models.URLField(blank=True, verbose_name="Thumbnail URL")
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

    def get_user_answer_display(self, user_answer):
        """Foydalanuvchi javobini ko'rsatish"""
        single_choice = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
        if self.question_type in single_choice:
            opts = {'a': self.option_a, 'b': self.option_b, 'c': self.option_c, 'd': self.option_d}
            return opts.get(str(user_answer).lower(), user_answer)
        return str(user_answer) if user_answer else ''
    
    def get_correct_answers_list(self):
        """To'g'ri javoblarni ro'yxat sifatida olish"""
        if self.correct_answer_json:
            return self.correct_answer_json
        if self.correct_answer:
            return [self.correct_answer]
        return []
    
    def check_user_answer(self, user_answer):
        """Foydalanuvchi javobi to'g'rimi tekshirish"""
        single_choice = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
        if self.question_type in single_choice:
            return str(user_answer).strip().lower() == str(self.correct_answer).strip().lower()
        
        fill_types = ('fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 
                      'table_completion', 'short_answer', 'matching_sentences', 'classification', 'list_selection')
        matching_types = ('matching_headings', 'matching_features', 'matching_info')
        
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
        
        # Fill-in types (list format)
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
        return all(norm(ua) == norm(ca) for ua, ca in zip(user_answers, correct_list))


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
        """Javobni tekshirish"""
        self.is_correct = self._is_answer_correct(self.user_answer)
        self.save()
        return self.is_correct
    
    def _is_answer_correct(self, user_answer):
        """Javob to'g'rimi tekshirish"""
        q = self.question
        if q.question_type in ('mcq', 'true_false'):
            return str(user_answer).strip().lower() == str(q.correct_answer).strip().lower()
        # fill_blank, summary_completion, notes_completion, short_answer
        correct_list = q.get_correct_answers_list()
        if not correct_list:
            return False
        # Bitta bo'sh joy - bitta javob
        if len(correct_list) == 1:
            return self._normalize_answer(user_answer) == self._normalize_answer(correct_list[0])
        # Bir nechta bo'sh joy - JSON yoki vergul bilan ajratilgan
        user_answers = self._parse_user_answers(user_answer, len(correct_list))
        if len(user_answers) != len(correct_list):
            return False
        for ua, ca in zip(user_answers, correct_list):
            if self._normalize_answer(ua) != self._normalize_answer(ca):
                return False
        return True
    
    @staticmethod
    def _normalize_answer(text):
        """Javobni solishtirish uchun normalizatsiya"""
        if text is None:
            return ''
        s = str(text).strip().lower()
        return ' '.join(s.split())
    
    @staticmethod
    def _parse_user_answers(user_answer, expected_count):
        """Foydalanuvchi javobini ro'yxatga ajratish"""
        import json
        if not user_answer:
            return []
        text = str(user_answer).strip()
        if text.startswith('[') or text.startswith('{'):
            try:
                data = json.loads(text)
                if isinstance(data, list):
                    return [str(x) for x in data]
                if isinstance(data, dict):
                    return [str(data.get(str(i+1), data.get(i, ''))) for i in range(expected_count)]
            except json.JSONDecodeError:
                pass
        return [text]


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
