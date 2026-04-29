from django.contrib import messages
from django.shortcuts import redirect

from core.access import get_user_module_access


class ModuleAccessMiddleware:
    """
    Namespace bo'yicha modul ruxsatlarini tekshiradi:
    - sat:* => SAT ruxsati kerak
    - core:* (module_selector dan tashqari) => IELTS ruxsati kerak
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None

        match = request.resolver_match
        if not match:
            return None

        access = get_user_module_access(request.user)
        namespace = match.namespace
        url_name = match.url_name

        if namespace == 'sat' and not access.can_access_sat:
            messages.error(request, "Sizga SAT bo'limiga kirish ruxsati berilmagan.")
            return redirect('core:module_selector')

        if namespace == 'core' and url_name != 'module_selector' and not access.can_access_ielts:
            messages.error(request, "Sizga IELTS bo'limiga kirish ruxsati berilmagan.")
            return redirect('core:module_selector')

        return None
