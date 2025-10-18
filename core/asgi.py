"""
ASGI config for SalesAiceAI project.

This module contains the ASGI application used by Django's development server
and any production ASGI deployments. It exposes the ASGI callable as a
module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/asgi/
"""

import os
import sys
import django
from django.core.asgi import get_asgi_application

# ============================================================================
# DJANGO SETTINGS CONFIGURATION
# ============================================================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# ============================================================================
# IMPORT CHANNELS AFTER DJANGO INITIALIZATION
# ============================================================================
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# ============================================================================
# IMPORT WEBSOCKET ROUTING WITH ERROR HANDLING
# ============================================================================
# Import WebSocket routing from both apps with graceful error handling
try:
    from calls.routing import websocket_urlpatterns as calls_websocket_patterns
    print("✅ Loaded calls WebSocket routing")
except ImportError as e:
    print(f"⚠️  Warning: Could not import calls.routing - {e}")
    calls_websocket_patterns = []

try:
    from HumeAiTwilio.routing import websocket_urlpatterns as hume_websocket_patterns
    print("✅ Loaded HumeAiTwilio WebSocket routing")
except ImportError as e:
    print(f"⚠️  Warning: Could not import HumeAiTwilio.routing - {e}")
    hume_websocket_patterns = []

# Combine all WebSocket patterns
all_websocket_patterns = calls_websocket_patterns + hume_websocket_patterns

# Log registered WebSocket routes for debugging
if all_websocket_patterns:
    print(f"📡 Registered {len(all_websocket_patterns)} WebSocket route(s):")
    for pattern in all_websocket_patterns:
        print(f"   - {pattern.pattern}")
else:
    print("⚠️  Warning: No WebSocket patterns registered!")

# ============================================================================
# CREATE ASGI APPLICATION
# ============================================================================
application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": django_asgi_app,
    
    # WebSocket handler with authentication middleware
    "websocket": AuthMiddlewareStack(
        URLRouter(all_websocket_patterns)
    ),
})

print("✅ ASGI application configured successfully")
print("="*80)
