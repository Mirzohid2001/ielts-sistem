from django.contrib.auth.models import User
from django.contrib import admin
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

    def test_inline_formset_save_new_no_duplicate(self):
        """Signal + formset.save_new → bitta yozuv (IntegrityError yo'q)."""
        from accounts.admin import UserModuleAccessInline
        from core.access import get_user_module_access

        user = get_user_model().objects.create_user(username='formsetuser', password='secret123')
        get_user_module_access(user)
        self.assertEqual(UserModuleAccess.objects.filter(user=user).count(), 1)

        FormSet = UserModuleAccessInline(User, admin.site).get_formset(None, obj=user)
        formset = FormSet(instance=user)
        Form = formset.form
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
        formset.save_new(form, commit=True)
        self.assertEqual(UserModuleAccess.objects.filter(user=user).count(), 1)
        access = UserModuleAccess.objects.get(user=user)
        self.assertFalse(access.can_access_sat)
        self.assertTrue(access.can_access_jobs)

    def test_admin_add_user_with_module_access_inline(self):
        """Admin /auth/user/add/ — IntegrityError va new_objects xatosiz."""
        import re

        admin_user = get_user_model().objects.create_superuser(
            username='adminadd', email='admin@test.com', password='adminpass',
        )
        self.client.force_login(admin_user)
        add_url = reverse('admin:auth_user_add')
        get_response = self.client.get(add_url)
        self.assertEqual(get_response.status_code, 200)
        html = get_response.content.decode()
        names = set(re.findall(r'name="([^"]+)"', html))

        inline_data = {}
        for total_name in sorted(n for n in names if n.endswith('-TOTAL_FORMS')):
            prefix = total_name.rsplit('-', 1)[0]
            has_access_fields = f'{prefix}-0-can_access_ielts' in names
            inline_data[f'{prefix}-TOTAL_FORMS'] = '1' if has_access_fields else '0'
            inline_data[f'{prefix}-INITIAL_FORMS'] = '0'
            inline_data[f'{prefix}-MIN_NUM_FORMS'] = '0'
            inline_data[f'{prefix}-MAX_NUM_FORMS'] = '1000'
            if has_access_fields:
                inline_data[f'{prefix}-0-can_access_ielts'] = 'on'
                inline_data[f'{prefix}-0-can_access_sat'] = 'on'
                inline_data[f'{prefix}-0-can_access_jobs'] = ''

        response = self.client.post(
            add_url,
            {
                'username': 'newadminuser',
                'password1': 'ComplexPass123!',
                'password2': 'ComplexPass123!',
                'is_active': 'on',
                'is_staff': 'on',
                **inline_data,
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302, response.content.decode()[:2000])
        user = get_user_model().objects.get(username='newadminuser')
        self.assertEqual(UserModuleAccess.objects.filter(user=user).count(), 1)
        access = UserModuleAccess.objects.get(user=user)
        self.assertTrue(access.can_access_ielts)
        self.assertTrue(access.can_access_sat)
        self.assertFalse(access.can_access_jobs)

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
