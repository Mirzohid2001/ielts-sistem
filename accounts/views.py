from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.conf import settings
from django.contrib.sessions.models import Session
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from .forms import OTPLoginForm
from .models import UserOTP
from core.models import UserActivity
from core.access import get_user_module_access


def login_view(request):
    """OTP bilan kirish"""
    if request.user.is_authenticated:
        return redirect('core:module_selector')
    
    if request.method == 'POST':
        form = OTPLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            otp_code = form.cleaned_data['otp_code']
            
            try:
                from django.contrib.auth.models import User
                user = User.objects.get(username=username)
                
                # OTP ni tekshirish
                otp = UserOTP.objects.filter(
                    user=user,
                    otp_code=otp_code,
                ).order_by('-created_at').first()
                
                if otp and otp.is_valid():
                    access = get_user_module_access(user)
                    active_session_key = access.active_session_key
                    if active_session_key and Session.objects.filter(
                        session_key=active_session_key,
                        expire_date__gt=timezone.now()
                    ).exists():
                        error_msg = "Bu kod bilan allaqachon tizimga kirilgan. Avval oldingi sessiyadan chiqing."
                        if request.headers.get('HX-Request'):
                            form.add_error('otp_code', error_msg)
                        else:
                            messages.error(request, error_msg)
                        return render(request, 'accounts/login.html', {'form': form})

                    # Login qilish
                    login(request, user)
                    if not request.session.session_key:
                        request.session.save()
                    
                    # Faqat single-use yoqilgan bo'lsa ishlatilgan deb belgilaymiz
                    if getattr(settings, 'OTP_SINGLE_USE', False):
                        otp.mark_as_used()
                    access.active_session_key = request.session.session_key
                    access.save(update_fields=['active_session_key', 'updated_at'])
                    
                    # Faollik yozish
                    UserActivity.objects.create(
                        user=user,
                        activity_type='login',
                        metadata={'ip': request.META.get('REMOTE_ADDR')}
                    )
                    
                    messages.success(request, 'Muvaffaqiyatli kirdingiz!')
                    
                    # HTMX request bo'lsa JSON qaytarish
                    if request.headers.get('HX-Request'):
                        return JsonResponse({
                            'success': True,
                            'redirect': '/'
                        })
                    
                    return redirect('core:module_selector')
                else:
                    error_msg = "Noto'g'ri kod."
                    if request.headers.get('HX-Request'):
                        form.add_error('otp_code', error_msg)
                    else:
                        messages.error(request, error_msg)
            except User.DoesNotExist:
                error_msg = "Bunday foydalanuvchi topilmadi."
                if request.headers.get('HX-Request'):
                    form.add_error('username', error_msg)
                else:
                    messages.error(request, error_msg)
    else:
        form = OTPLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Chiqish"""
    from django.contrib.auth import logout
    if request.user.is_authenticated:
        access = get_user_module_access(request.user)
        if access.active_session_key == request.session.session_key:
            access.active_session_key = None
            access.save(update_fields=['active_session_key', 'updated_at'])
    logout(request)
    messages.success(request, 'Tizimdan chiqdingiz.')
    return redirect('accounts:login')
