# Real-time updates via Twilio webhooks - see webhook_handlers.py
# Webhook endpoints handle call status updates, agent metrics, and campaign progress
# This provides reliable real-time updates without WebSocket complexity

# Webhook URL patterns:
# /agents/webhooks/status/ - Main webhook for call status updates  
# /agents/webhooks/voice/ - Voice call handling with agent scripts
# /agents/webhooks/recording-complete/ - Handle recording completions
# /agents/webhooks/callback/ - General status callbacks

# Django URL configuration for webhook endpoints
from django.urls import path
from . import webhook_handlers

webhook_urlpatterns = [
    path('webhooks/status/', webhook_handlers.TwilioAgentWebhookView.as_view(), name='twilio_status_webhook'),
    path('webhooks/voice/', webhook_handlers.twilio_voice_webhook, name='twilio_voice_webhook'),
    path('webhooks/recording-complete/', webhook_handlers.twilio_recording_complete, name='twilio_recording_webhook'),
    path('webhooks/callback/', webhook_handlers.twilio_status_callback, name='twilio_callback_webhook'),
]