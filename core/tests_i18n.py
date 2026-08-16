from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from core.models import UserModuleAccess
from core.services.ai_language import COOKIE_NAME, SESSION_KEY


class SiteLanguageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='i18nuser',
            password='pass12345',
            first_name='Ali',
        )
        UserModuleAccess.objects.get_or_create(user=self.user)

    def test_login_default_is_uzbek(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tizimga kirish')
        self.assertNotContains(response, 'Вход в систему')

    def test_switch_language_sets_cookie_and_session(self):
        response = self.client.post(
            reverse('set_site_language'),
            {'ai_lang': 'ru', 'next': reverse('accounts:login')},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.cookies.get(COOKIE_NAME).value, 'ru')
        session = self.client.session
        self.assertEqual(session.get(SESSION_KEY), 'ru')

    def test_login_page_shows_russian_after_switch(self):
        self.client.post(
            reverse('set_site_language'),
            {'ai_lang': 'ru', 'next': reverse('accounts:login')},
        )
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, 'Вход в систему')
        self.assertContains(response, 'Войти')
        self.assertNotContains(response, 'Tizimga kirish')

    def test_module_selector_russian(self):
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('core:module_selector'))
        self.assertContains(response, 'Выберите раздел')
        self.assertContains(response, 'Разделы')
        self.assertNotContains(response, "Bo'limni tanlang")

    def test_dashboard_russian_chrome(self):
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('core:dashboard'))
        self.assertContains(response, 'Добро пожаловать')
        self.assertContains(response, 'Главная')
        self.assertContains(response, 'Тесты')

    def test_cookie_alone_activates_russian(self):
        self.client.cookies[COOKIE_NAME] = 'ru'
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, 'Вход в систему')

    def test_admin_ignores_russian_cookie(self):
        admin = get_user_model().objects.create_superuser(
            username='i18nadmin',
            email='a@example.com',
            password='pass12345',
        )
        self.client.force_login(admin)
        self.client.cookies[COOKIE_NAME] = 'ru'
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Вход в систему')
        self.assertNotContains(response, 'Выберите раздел')

    def test_json_language_switch(self):
        response = self.client.post(
            reverse('set_site_language'),
            data='{"ai_lang":"ru"}',
            content_type='application/json',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['lang'], 'ru')
        self.assertEqual(self.client.cookies.get(COOKIE_NAME).value, 'ru')

    def test_switch_back_to_uzbek(self):
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        self.client.post(
            reverse('set_site_language'),
            {'ai_lang': 'uz', 'next': reverse('accounts:login')},
        )
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, 'Tizimga kirish')
        self.assertNotContains(response, 'Вход в систему')

    def test_test_list_russian_chrome(self):
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('core:test_list'))
        self.assertContains(response, 'Поиск')
        self.assertContains(response, 'Название теста, категория...')
        self.assertNotContains(response, 'Test nomi, kategoriya...')

    def test_sat_home_russian_chrome(self):
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('sat:sat_home'))
        self.assertContains(response, 'Направление SAT')
        self.assertContains(response, 'Математика')
        self.assertContains(response, 'Разделы')
        self.assertContains(response, 'Сохранено видео/PDF')
        self.assertNotContains(response, 'ta resurs')
        self.assertNotContains(response, "Bo'limlar")

    def test_profile_and_notifications_russian_leftovers(self):
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        profile = self.client.get(reverse('core:profile'))
        self.assertContains(profile, 'Последняя активность SAT')
        self.assertContains(profile, 'В разделе SAT пока нет активности.')
        self.assertContains(profile, 'Тесты:')
        self.assertContains(profile, 'Видео:')
        self.assertContains(profile, 'Ресурсы:')
        self.assertContains(profile, 'Скоро')
        self.assertNotContains(profile, "SAT bo'limida hali faollik yo'q.")
        self.assertNotContains(profile, 'Testlar:')
        ielts = self.client.get(reverse('core:profile_section', args=['ielts']))
        self.assertContains(ielts, 'Результаты тестов')
        self.assertContains(ielts, 'Дата')
        self.assertContains(ielts, 'Статус')
        self.assertContains(ielts, 'средний')
        self.assertNotContains(ielts, 'Export (CSV)')
        self.assertNotContains(ielts, "% o'rtacha")
        notes = self.client.get(reverse('core:notifications'))
        self.assertContains(notes, 'Уведомлений пока нет.')
        self.assertNotContains(notes, "Hozircha bildirishnoma yo'q.")

    def test_test_list_recommended_copy_russian(self):
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('core:test_list'))
        self.assertNotContains(response, "Sizning darajangizga mos testlar")

    def test_js_catalog_includes_last_choice_russian(self):
        from core.i18n_js import js_catalog

        with translation.override('ru'):
            self.assertEqual(js_catalog()['Oxirgi tanlov'], 'Последний выбор')

    def test_sat_access_denied_message_russian(self):
        access = UserModuleAccess.objects.get(user=self.user)
        access.can_access_sat = False
        access.save(update_fields=['can_access_sat'])
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('sat:sat_home'), follow=True)
        self.assertContains(response, 'У вас нет доступа к разделу SAT.')
        self.assertNotContains(response, "Sizga SAT bo'limiga kirish ruxsati berilmagan.")

    def test_sat_subject_filter_russian(self):
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('sat:sat_subject', args=['math']))
        self.assertContains(response, 'Только PDF')
        self.assertContains(response, 'Фильтровать')
        self.assertNotContains(response, 'Faqat PDF')

    def test_test_list_count_russian(self):
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('core:test_list'))
        self.assertNotContains(response, 'ta test topildi')

    def test_analytics_table_headers_russian(self):
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('core:analytics'))
        self.assertContains(response, 'Не сдан')
        self.assertContains(response, 'Экспорт:')
        self.assertNotContains(response, "O'tmagan")

    def test_dashboard_translates_category_descriptions(self):
        from core.models import Category

        Category.objects.create(
            name='Reading',
            slug='reading-i18n',
            description='Reading testlari',
            is_active=True,
            show_on_site=True,
        )
        Category.objects.create(
            name='Listening',
            slug='listening-i18n',
            description='Listening testlari',
            is_active=True,
            show_on_site=True,
        )
        self.client.login(username='i18nuser', password='pass12345')
        self.client.post(reverse('set_site_language'), {'ai_lang': 'ru', 'next': '/'})
        response = self.client.get(reverse('core:dashboard'))
        self.assertContains(response, 'Тесты Reading')
        self.assertContains(response, 'Тесты Listening')
        self.assertNotContains(response, 'Reading testlari')
        self.assertNotContains(response, 'Listening testlari')

    def test_site_t_translates_testlari_blurbs(self):
        from core.templatetags.core_filters import site_t

        with translation.override('ru'):
            self.assertEqual(site_t('Reading testlari'), 'Тесты Reading')
            self.assertEqual(site_t('IELTS Writing testlari'), 'Тесты IELTS Writing')
            self.assertEqual(
                site_t("IELTS Writing bo'yicha medium darajadagi test. Barcha savol turlarini o'z ichiga oladi."),
                'Тест IELTS Writing, уровень: Средний. Включает все типы вопросов.',
            )
            self.assertEqual(
                site_t("IELTS Reading bo'yicha oson darajadagi amaliy test. 10 ta savol."),
                'Практический тест IELTS Reading, уровень: Лёгкий. 10 вопросов.',
            )
        with translation.override('uz'):
            self.assertEqual(site_t('Reading testlari'), 'Reading testlari')
            self.assertEqual(
                site_t("IELTS Writing bo'yicha medium darajadagi test. Barcha savol turlarini o'z ichiga oladi."),
                "IELTS Writing bo'yicha medium darajadagi test. Barcha savol turlarini o'z ichiga oladi.",
            )

    def test_middleware_activates_translation(self):
        self.client.cookies[COOKIE_NAME] = 'ru'
        with translation.override('uz'):
            response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, 'Вход в систему')
