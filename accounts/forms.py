from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
from crispy_bootstrap5.bootstrap5 import FloatingField


class OTPLoginForm(forms.Form):
    """OTP bilan kirish formasi"""
    username = forms.CharField(
        max_length=150,
        label="Foydalanuvchi nomi",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Foydalanuvchi nomini kiriting',
            'autocomplete': 'username'
        })
    )
    otp_code = forms.CharField(
        max_length=20,
        label="OTP Kod",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'OTP kodni kiriting',
            'autocomplete': 'off'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.attrs = {
            'hx-post': '',
            'hx-target': '#login-form-container',
            'hx-swap': 'innerHTML'
        }
        self.helper.layout = Layout(
            Row(
                Column('username', css_class='mb-3'),
            ),
            Row(
                Column('otp_code', css_class='mb-3'),
            ),
            Submit('submit', 'Kirish', css_class='btn btn-primary w-100'),
        )

