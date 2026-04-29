"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

from core.views import admin_toliq_yoriqnoma


def favicon_view(request):
    """Brauzer /favicon.ico so'rovini 404 bermaslik uchun (admin va asosiy sahifa)."""
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🎓</text></svg>'
    return HttpResponse(svg, content_type='image/svg+xml; charset=utf-8')


urlpatterns = [
    path('favicon.ico', favicon_view),
    path('admin/yoriqnoma/', admin_toliq_yoriqnoma, name='admin_toliq_yoriqnoma'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('sat/', include('sat.urls')),
    path('', include('core.urls')),
]

# Media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
