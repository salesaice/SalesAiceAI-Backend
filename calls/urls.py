from django.urls import path
from . import views
from . import auto_voice_integration

urlpatterns = [
    path('sessions/', views.CallSessionsAPIView.as_view(), name='call-sessions'),
    path('queue/', views.CallQueueAPIView.as_view(), name='call-queue'),
    path('start-call/', views.StartCallAPIView.as_view(), name='start-call'),
    path('twilio-webhook/', views.TwilioWebhookAPIView.as_view(), name='twilio-webhook'),
    path('ai-assistance/', views.HomeAIIntegrationAPIView.as_view(), name='homeai-assistance'),
    path('quick-actions/', views.QuickActionsAPIView.as_view(), name='quick-actions'),
    
    # AUTO VOICE SYSTEM - ENABLED FOR LIVE CALLS
    path('auto-voice-call/', auto_voice_integration.AutoVoiceCallAPIView.as_view(), name='auto-voice-call'),
    path('auto-voice-webhook/', auto_voice_integration.AutoVoiceWebhookView.as_view(), name='auto-voice-webhook'),
    
    # Voice Response for Twilio (REQUIRED for agent response)
    path('voice-response/', views.voice_response_handler, name='voice-response'),   # POST/GET /api/calls/voice-response/
    path('call-status/', views.call_status_handler, name='call-status'),           # POST /api/calls/call-status/
    
    # Call Data API - Frontend Interface
    path('data/', views.call_data_list, name='call-data-list'),                    # GET /api/calls/data/
    path('data/<uuid:call_id>/', views.call_detail, name='call-detail'),          # GET /api/calls/data/{call_id}/
    
    # Real-time Updates
    path('broadcast/', views.broadcast_live_update, name='broadcast-live-update'), # POST /api/calls/broadcast/
    path('websocket-info/', views.websocket_info, name='websocket-info'),         # GET /api/calls/websocket-info/
    
    # Twilio Webhook Handlers
    path('fallback/', views.fallback_handler, name='fallback-handler'),           # POST /api/calls/fallback/
    path('status-callback/', views.status_callback, name='status-callback'),      # POST /api/calls/status-callback/
]
