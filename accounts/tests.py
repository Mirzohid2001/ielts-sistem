from django.contrib.auth.models import User
from django.test import TestCase
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from accounts.models import UserOTP
from core.models import UserModuleAccess


class AccountAccessFlowTests(TestCase):
    def test_user_creation_also_creates_module_access(self):
        user = get_user_model().objects.create_user(username='newuser', password='secret123')
        self.assertTrue(UserModuleAccess.objects.filter(user=user).exists())

    def test_admin_inline_save_new_does_not_duplicate_module_access(self):
        """Signal + inline: bitta UserModuleAccess bo'lishi kerak (IntegrityError yo'q)."""
        from django.contrib.admin.sites import AdminSite
        from accounts.admin import UserModuleAccessInline
        from core.access import get_user_module_access

        user = get_user_model().objects.create_user(username='inlinetest', password='secret123')
        get_user_module_access(user)
        self.assertEqual(UserModuleAccess.objects.filter(user=user).count(), 1)

        inline = UserModuleAccessInline(User, AdminSite())
        Form = inline.get_formset(None, obj=user).form
        form = Form(
            data={
                'user': user.pk,
                'can_access_ielts': True,
                'can_access_sat': False,
                'can_access_jobs': True,
            },
            instance=UserModuleAccess(user=user),
        )
        self.assertTrue(form.is_valid(), form.errors)
        inline.save_new(form, commit=True)
        self.assertEqual(UserModuleAccess.objects.filter(user=user).count(), 1)
        access = UserModuleAccess.objects.get(user=user)
        self.assertFalse(access.can_access_sat)
        self.assertTrue(access.can_access_jobs)

    def test_authenticated_user_login_page_redirects_to_module_selector(self):
        user = get_user_model().objects.create_user(username='authuser', password='secret123')
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:module_selector'))

    def test_successful_otp_login_redirects_to_module_selector(self):
        user = get_user_model().objects.create_user(username='otpuser', password='secret123')
        UserOTP.objects.create(
            user=user,
            otp_code='1234567890',
            is_used=False,
            expires_at=timezone.now() + timedelta(hours=1),
        )

        response = self.client.post(
            reverse('accounts:login'),
            data={'username': 'otpuser', 'otp_code': '1234567890'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:module_selector'))

    def test_used_otp_still_works_when_single_use_disabled(self):
        user = get_user_model().objects.create_user(username='usedotp', password='secret123')
        UserOTP.objects.create(
            user=user,
            otp_code='7777777777',
            is_used=True,
            used_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() - timedelta(days=2),
        )

        response = self.client.post(
            reverse('accounts:login'),
            data={'username': 'usedotp', 'otp_code': '7777777777'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:module_selector'))

    def test_expired_otp_still_works_when_expiry_check_disabled(self):
        user = get_user_model().objects.create_user(username='expiredotp', password='secret123')
        UserOTP.objects.create(
            user=user,
            otp_code='8888888888',
            is_used=False,
            expires_at=timezone.now() - timedelta(days=10),
        )

        response = self.client.post(
            reverse('accounts:login'),
            data={'username': 'expiredotp', 'otp_code': '8888888888'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:module_selector'))

    def test_prevent_concurrent_login_with_same_code(self):
        user = get_user_model().objects.create_user(username='singlelogin', password='secret123')
        UserOTP.objects.create(
            user=user,
            otp_code='9999999999',
            is_used=False,
            expires_at=timezone.now() + timedelta(days=1),
        )

        first_client = Client()
        second_client = Client()

        first_response = first_client.post(
            reverse('accounts:login'),
            data={'username': 'singlelogin', 'otp_code': '9999999999'},
        )
        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(first_response.url, reverse('core:module_selector'))

        second_response = second_client.post(
            reverse('accounts:login'),
            data={'username': 'singlelogin', 'otp_code': '9999999999'},
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertContains(second_response, "Bu kod bilan allaqachon tizimga kirilgan")

    def test_logout_releases_single_login_lock(self):
        user = get_user_model().objects.create_user(username='unlocklogin', password='secret123')
        UserOTP.objects.create(
            user=user,
            otp_code='6666666666',
            is_used=False,
            expires_at=timezone.now() + timedelta(days=1),
        )

        first_client = Client()
        second_client = Client()

        first_login = first_client.post(
            reverse('accounts:login'),
            data={'username': 'unlocklogin', 'otp_code': '6666666666'},
        )
        self.assertEqual(first_login.status_code, 302)

        first_logout = first_client.get(reverse('accounts:logout'))
        self.assertEqual(first_logout.status_code, 302)

        second_login = second_client.post(
            reverse('accounts:login'),
            data={'username': 'unlocklogin', 'otp_code': '6666666666'},
        )
        self.assertEqual(second_login.status_code, 302)
        self.assertEqual(second_login.url, reverse('core:module_selector'))
