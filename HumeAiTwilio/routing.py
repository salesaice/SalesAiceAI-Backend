"""
Routing configuration for WebSocket connections
FIXED: Added ^ prefix to all regex patterns for proper URL matching
"""

from django.urls import re_path
from . import consumers
from .twilio_consumers import TwilioHumeStreamConsumer
from .twilio_hume_evi_consumer import TwilioHumeEVIConsumer  # NEW: Real HumeAI EVI
from .hume_realtime_consumer import HumeTwilioRealTimeConsumer  # LATEST: Full integration

websocket_urlpatterns = [
    # REMOVED: Old placeholder route (was causing conflicts)
    # re_path(r'^ws/hume-twilio/stream/$', consumers.HumeTwilioStreamConsumer.as_asgi()),
    
    # Twilio Voice Stream endpoint (legacy, keeping for compatibility)
    re_path(r'^api/hume-twilio/stream/(?P<call_sid>[^/]+)/?$', TwilioHumeStreamConsumer.as_asgi()),
    
    # HumeAI EVI WebSocket endpoint (alternative implementation)
    re_path(r'^ws/hume-twilio/evi/(?P<call_sid>[^/]+)/?$', TwilioHumeEVIConsumer.as_asgi()),
    
    # MAIN ROUTE: Full HumeAI real-time integration (PRODUCTION) - FIXED: Optional trailing slash
    re_path(r'^ws/hume-twilio/stream/(?P<call_sid>[^/]+)/?$', HumeTwilioRealTimeConsumer.as_asgi()),
]
