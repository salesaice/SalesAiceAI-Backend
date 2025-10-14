from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.CallSessionsAPIView.as_view(), name='call-sessions'),
    path('queue/', views.CallQueueAPIView.as_view(), name='call-queue'),
    path('start-call/', views.StartCallAPIView.as_view(), name='start-call'),
    path('twilio-webhook/', views.TwilioWebhookAPIView.as_view(), name='twilio-webhook'),
    path('ai-assistance/', views.HomeAIIntegrationAPIView.as_view(), name='homeai-assistance'),
    path('quick-actions/', views.QuickActionsAPIView.as_view(), name='quick-actions'),
    
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
