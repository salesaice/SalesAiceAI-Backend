from django.urls import path
from . import views

# Lazy import function for auto voice integration
def get_auto_voice_call_view(*args, **kwargs):
    from . import auto_voice_integration
    return auto_voice_integration.AutoVoiceCallAPIView.as_view()(*args, **kwargs)

def get_auto_voice_webhook_view(*args, **kwargs):
    from . import auto_voice_integration
    return auto_voice_integration.AutoVoiceWebhookView.as_view()(*args, **kwargs)

# Lazy import for enhanced voice webhook (HYBRID SYSTEM)
def get_enhanced_voice_webhook_view(*args, **kwargs):
    from . import enhanced_voice_webhook
    return enhanced_voice_webhook.EnhancedAutoVoiceWebhookView.as_view()(*args, **kwargs)

# Lazy import for HumeAI webhook handlers
def get_hume_webhook_view(*args, **kwargs):
    from . import hume_webhook_handlers
    return hume_webhook_handlers.hume_ai_webhook(*args, **kwargs)

def get_hume_status_view(*args, **kwargs):
    from . import hume_webhook_handlers
    return hume_webhook_handlers.hume_ai_status_callback(*args, **kwargs)

def get_hume_config_test_view(*args, **kwargs):
    from . import hume_webhook_handlers
    return hume_webhook_handlers.hume_ai_config_test(*args, **kwargs)

# Lazy import for PRODUCTION voice webhook (FINAL SYSTEM)
def get_production_voice_webhook_view(*args, **kwargs):
    from . import production_voice_webhook
    return production_voice_webhook.get_production_voice_webhook_view()(*args, **kwargs)

# Lazy import for FINAL PRODUCTION webhook (ALL 5 ISSUES FIXED)
def get_final_production_voice_webhook_view(*args, **kwargs):
    from . import final_production_voice_webhook
    return final_production_voice_webhook.get_final_production_voice_webhook_view()(*args, **kwargs)

# Lazy import for ULTIMATE PRODUCTION webhook (ALL NEW ISSUES FIXED)
def get_ultimate_production_voice_webhook_view(*args, **kwargs):
    from . import ultimate_production_voice_webhook
    return ultimate_production_voice_webhook.get_ultimate_production_voice_webhook_view()(*args, **kwargs)

def get_pure_hume_webhook_view(*args, **kwargs):
    from .pure_hume_ai_webhook import PureHumeAIVoiceWebhook
    return PureHumeAIVoiceWebhook.as_view()(*args, **kwargs)

urlpatterns = [
    path('sessions/', views.CallSessionsAPIView.as_view(), name='call-sessions'),
    path('queue/', views.CallQueueAPIView.as_view(), name='call-queue'),
    path('start-call/', views.StartCallAPIView.as_view(), name='start-call'),
    path('twilio-webhook/', views.TwilioWebhookAPIView.as_view(), name='twilio-webhook'),
    path('ai-assistance/', views.HomeAIIntegrationAPIView.as_view(), name='homeai-assistance'),
    path('quick-actions/', views.QuickActionsAPIView.as_view(), name='quick-actions'),
    
    # AUTO VOICE SYSTEM - ENABLED FOR LIVE CALLS (lazy imported to avoid migration warnings)
    path('auto-voice-call/', get_auto_voice_call_view, name='auto-voice-call'),
    path('auto-voice-webhook/', get_auto_voice_webhook_view, name='auto-voice-webhook'),
    
    # ENHANCED VOICE WEBHOOK - Real-time customer listening (OLD - has hardcoded responses)
    path('enhanced-voice-webhook/', get_enhanced_voice_webhook_view, name='enhanced-voice-webhook'),
    
    # PURE HUME AI WEBHOOK - NOW REDIRECTED TO ULTIMATE PRODUCTION
    path('pure-hume-webhook/', get_ultimate_production_voice_webhook_view, name='pure-hume-webhook'),
    
    # HUME AI WEBHOOKS - Real-time conversation handling
    path('hume-webhook/', get_hume_webhook_view, name='hume-webhook'),           # POST /api/calls/hume-webhook/
    path('hume-status/', get_hume_status_view, name='hume-status'),             # POST /api/calls/hume-status/
    path('hume-config/', get_hume_config_test_view, name='hume-config'),        # GET/POST /api/calls/hume-config/
    
    # Voice Response for Twilio (REQUIRED for agent response) - NOW USING ULTIMATE PRODUCTION WEBHOOK
    path('voice-response/', get_ultimate_production_voice_webhook_view, name='voice-response'),   # POST/GET /api/calls/voice-response/
    path('call-status/', views.call_status_handler, name='call-status'),           # POST /api/calls/call-status/
    
    # REAL-TIME WEBHOOK TESTING - Local Development
    path('test-webhook/', views.test_webhook_handler, name='test-webhook'),         # POST/GET /api/calls/test-webhook/
    path('webhook-status/', views.webhook_status_checker, name='webhook-status'),  # GET /api/calls/webhook-status/
    
    # Call Data API - Frontend Interface
    path('data/', views.call_data_list, name='call-data-list'),                    # GET /api/calls/data/
    path('data/<uuid:call_id>/', views.call_detail, name='call-detail'),          # GET /api/calls/data/{call_id}/
    
    # Real-time Updates
    path('broadcast/', views.broadcast_live_update, name='broadcast-live-update'), # POST /api/calls/broadcast/
    path('websocket-info/', views.websocket_info, name='websocket-info'),         # GET /api/calls/websocket-info/
    
    # Twilio Webhook Handlers
    path('fallback/', views.fallback_handler, name='fallback-handler'),           # POST /api/calls/fallback/
    path('status-callback/', views.status_callback, name='status-callback'),      # POST /api/calls/status-callback/
    
    # PRODUCTION VOICE WEBHOOK - Final system with all fixes
    path('production-voice-webhook/', get_production_voice_webhook_view, name='production-voice-webhook'),  # POST /api/calls/production-voice-webhook/
    
    # FINAL PRODUCTION WEBHOOK - ALL 5 ISSUES FIXED
    path('final-production-webhook/', get_final_production_voice_webhook_view, name='final-production-webhook'),  # POST /api/calls/final-production-webhook/
    
    # ULTIMATE PRODUCTION WEBHOOK - ALL NEW ISSUES FIXED (Voice matching, Training, Interrupts, Live Analysis, Live Config)
    path('ultimate-production-webhook/', get_ultimate_production_voice_webhook_view, name='ultimate-production-webhook'),  # POST /api/calls/ultimate-production-webhook/
]
