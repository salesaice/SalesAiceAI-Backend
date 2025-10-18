import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Import WebSocket routing from both apps
from calls.routing import websocket_urlpatterns as calls_websocket_patterns
from HumeAiTwilio.routing import websocket_urlpatterns as hume_websocket_patterns

# Combine all WebSocket patterns
all_websocket_patterns = calls_websocket_patterns + hume_websocket_patterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(all_websocket_patterns)
    ),
})
