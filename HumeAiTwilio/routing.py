"""
Routing configuration for WebSocket connections
"""

from django.urls import re_path
from . import consumers
from .twilio_consumers import TwilioHumeStreamConsumer
from .twilio_hume_evi_consumer import TwilioHumeEVIConsumer  # NEW: Real HumeAI EVI

websocket_urlpatterns = [
    # Original WebSocket endpoint
    re_path(r'ws/hume-twilio/stream/$', consumers.HumeTwilioStreamConsumer.as_asgi()),
    
    # Twilio Voice Stream endpoint
    re_path(r'api/hume-twilio/stream/(?P<call_sid>[^/]+)$', TwilioHumeStreamConsumer.as_asgi()),
    
    # NEW: HumeAI EVI WebSocket endpoint (Real-time with emotion detection)
    re_path(r'ws/hume-twilio/evi/(?P<call_sid>[^/]+)/$', TwilioHumeEVIConsumer.as_asgi()),
]
