import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TechCampuss.settings')

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import ChatApp.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(
        ChatApp.routing.websocket_urlpatterns
    ),
})
