# your_project/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import TechApp.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TechCampuss.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            TechApp.routing.websocket_urlpatterns
        )
    ),
})