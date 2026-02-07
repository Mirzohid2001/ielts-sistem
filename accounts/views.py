from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .forms import OTPLoginForm
from .models import UserOTP
from core.models import UserActivity


def login_view(request):
    """OTP bilan kirish"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
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
                    is_used=False
                ).first()
                
                if otp and otp.is_valid():
                    # Login qilish
                    login(request, user)
                    
                    # OTP ni ishlatilgan deb belgilash
                    otp.mark_as_used()
                    
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
                    
                    return redirect('core:dashboard')
                else:
                    error_msg = "Noto'g'ri OTP kod yoki kodning muddati o'tgan."
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
    logout(request)
    messages.success(request, 'Tizimdan chiqdingiz.')
    return redirect('accounts:login')
