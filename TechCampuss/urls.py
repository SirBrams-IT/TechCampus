from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Override admin login
def custom_admin_login(request):
    return redirect(settings.LOGIN_URL)

urlpatterns = [
    path('', include('TechApp.urls')),  
    path('', include('ChatApp.urls')), 
    path("chatbot/", include("chatbot.urls")),
    path("accounts/", include("allauth.urls")),

    # Override admin login
    path('admin/login/', custom_admin_login, name='custom-admin-login'),

    # Admin route MUST appear AFTER the override login
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
