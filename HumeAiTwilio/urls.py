"""
URL Configuration for HumeAI + Twilio Integration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    HumeAgentViewSet,
    TwilioCallViewSet,
    ConversationLogViewSet,
    CallAnalyticsViewSet,
    twilio_webhook,
    twilio_twiml,
    hume_webhook,
    dashboard_stats,
    recent_calls,
)

# NEW: Import Twilio Voice Bridge (WebSocket version)
from .twilio_voice_bridge import (
    twilio_voice_webhook,
    twilio_status_callback,
)

# NEW: Import Simple Voice (NO WebSocket - FREE version)
from .twilio_simple_voice import (
    twilio_voice_webhook_simple,
    process_speech_simple,
    twilio_status_callback_simple,
)

app_name = 'HumeAiTwilio'

# Router for ViewSets
router = DefaultRouter()
router.register(r'agents', HumeAgentViewSet, basename='agent')
router.register(r'calls', TwilioCallViewSet, basename='call')
router.register(r'conversations', ConversationLogViewSet, basename='conversation')
router.register(r'analytics', CallAnalyticsViewSet, basename='analytics')

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Webhook endpoints (original)
    path('webhooks/twilio/', twilio_webhook, name='twilio-webhook'),
    path('webhooks/twilio/twiml/', twilio_twiml, name='twilio-twiml'),
    path('webhooks/hume/', hume_webhook, name='hume-webhook'),
    
    # NEW: Twilio Voice Bridge endpoints (WebSocket - requires paid plan)
    path('voice-webhook/', twilio_voice_webhook, name='twilio-voice-webhook'),
    path('status-callback/', twilio_status_callback, name='twilio-status-callback'),
    
    # NEW: Simple Voice endpoints (NO WebSocket - FREE PythonAnywhere)
    path('voice-webhook-simple/', twilio_voice_webhook_simple, name='voice-webhook-simple'),
    path('process-speech-simple/', process_speech_simple, name='process-speech-simple'),
    path('status-callback-simple/', twilio_status_callback_simple, name='status-callback-simple'),
    
    # Dashboard endpoints
    path('dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('dashboard/recent-calls/', recent_calls, name='recent-calls'),
]
