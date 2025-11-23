from django.shortcuts import redirect
from django.conf import settings

class RedirectAdminLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Force redirect from Django admin login to your login page
        if request.path.startswith("/admin/login/"):
            return redirect(settings.LOGIN_URL)

        return self.get_response(request)
