"""
Routing configuration for WebSocket connections
PRODUCTION: Using HumeTwilioRealTimeConsumer for complete HumeAI EVI integration
"""

from django.urls import re_path
from .hume_realtime_consumer import HumeTwilioRealTimeConsumer  # MAIN: Full HumeAI EVI integration

websocket_urlpatterns = [
    # MAIN PRODUCTION ROUTE: Complete HumeAI + Twilio real-time integration
    # This handles all voice calls with full EVI support
    re_path(r'^ws/hume-twilio/stream/(?P<call_sid>[^/]+)/?$', HumeTwilioRealTimeConsumer.as_asgi()),
    
    # Alternative path (same consumer, different URL pattern for compatibility)
    re_path(r'^api/hume-twilio/stream/(?P<call_sid>[^/]+)/?$', HumeTwilioRealTimeConsumer.as_asgi()),
]

# NOTE: Old routes removed to avoid conflicts:
# - TwilioHumeStreamConsumer (was causing "Handle media error" issues)
# - TwilioHumeEVIConsumer (incomplete implementation)
# - consumers.HumeTwilioStreamConsumer (placeholder only)
