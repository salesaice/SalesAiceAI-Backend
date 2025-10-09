"""
Twilio Integration Configuration for Real-time Agent Management

This file provides setup instructions and configuration for integrating
Twilio webhooks with the Agent Management system for real-time updates.
"""

# 1. TWILIO WEBHOOK CONFIGURATION
WEBHOOK_ENDPOINTS = {
    'status_callback': '/agents/webhooks/status/',
    'voice_webhook': '/agents/webhooks/voice/', 
    'recording_webhook': '/agents/webhooks/recording-complete/',
    'general_callback': '/agents/webhooks/callback/',
}

# 2. TWILIO PHONE NUMBER CONFIGURATION
"""
In your Twilio Console:
1. Go to Phone Numbers > Manage > Active numbers
2. Click on your Twilio phone number
3. Set these webhook URLs:

Voice & Fax:
- Webhook: https://yourdomain.com/agents/webhooks/voice/
- HTTP Method: POST

Status Callbacks:
- Status Callback URL: https://yourdomain.com/agents/webhooks/status/
- Method: POST
"""

# 3. AGENT CALL CONFIGURATION
AGENT_CALL_PARAMS = """
When making outbound calls via Twilio for agents:

client.calls.create(
    to=contact_phone,
    from_=agent_twilio_number,
    url='https://yourdomain.com/agents/webhooks/voice/',
    method='POST',
    status_callback='https://yourdomain.com/agents/webhooks/status/',
    status_callback_method='POST',
    status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
    # Include custom parameters
    send_digits='w1234#',  # If needed
    timeout=30,
    record=True if agent.call_recording_enabled else False
)
"""

# 4. CAMPAIGN AUTOMATION SETUP
CAMPAIGN_WEBHOOK_SETUP = """
For automated campaigns, pass campaign and agent IDs as URL parameters:

status_callback_url = f'https://yourdomain.com/agents/webhooks/status/?agent_id={agent.id}&campaign_id={campaign.id}'

This enables automatic tracking of:
- Agent performance metrics
- Campaign progress updates  
- Call queue management
- Real-time dashboard updates
"""

# 5. DJANGO URL INTEGRATION
"""
Add to your main urls.py:

from agents.routing import webhook_urlpatterns

urlpatterns = [
    # ... your existing patterns
    path('agents/', include('agents.urls')),
    path('agents/', include(webhook_urlpatterns)),
]
"""

# 6. SECURITY CONSIDERATIONS
SECURITY_SETUP = """
1. Validate Twilio signatures in production:
   - Install: pip install twilio
   - Add signature validation in webhook_handlers.py
   
2. Use HTTPS in production for all webhook URLs

3. Set up proper CORS headers if needed

4. Consider rate limiting for webhook endpoints
"""

# 7. TESTING WEBHOOKS LOCALLY
LOCAL_TESTING = """
For local development with ngrok:

1. Install ngrok: https://ngrok.com/
2. Run your Django server: python manage.py runserver
3. In another terminal: ngrok http 8000
4. Use the ngrok HTTPS URL in Twilio webhook configuration
5. Test with Twilio phone numbers

Example ngrok URL: https://abc123.ngrok.io/agents/webhooks/status/
"""

# 8. MONITORING AND LOGGING
MONITORING_SETUP = """
Monitor webhook performance:

1. Check Django logs for webhook processing
2. Use Twilio Console > Monitor > Logs for delivery status
3. Set up alerts for failed webhook deliveries
4. Monitor agent performance metrics in dashboard

Log locations:
- Webhook processing: agents/webhook_handlers.py logger
- Agent updates: agents/models_new.py
- Campaign progress: agents/views_new.py
"""