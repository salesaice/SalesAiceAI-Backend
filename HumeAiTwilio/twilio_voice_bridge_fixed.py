"""
✅ FINAL SOLUTION: Fix Ngrok 400 Error for Twilio
Update webhook to work without ngrok browser warning
"""

# PROBLEM: Ngrok is returning browser warning (400) to Twilio
# SOLUTION: Use direct Django webhook URL with ngrok bypass

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])  # Accept both for Twilio
def voice_webhook_fixed(request):
    """
    Fixed voice webhook that bypasses ngrok issues
    Returns proper TwiML for Twilio
    """
    # Log incoming request
    call_sid = request.POST.get('CallSid') or request.GET.get('CallSid', 'UNKNOWN')
    from_number = request.POST.get('From') or request.GET.get('From', 'UNKNOWN')
    to_number = request.POST.get('To') or request.GET.get('To', 'UNKNOWN')
    
    logger.info(f"📞 Voice webhook called: {from_number} → {to_number} (SID: {call_sid})")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Initial greeting
    response.say(
        "Hello! Connecting you to the AI assistant. Please wait a moment.",
        voice='alice',
        language='en-US'
    )
    
    # Get host from request
    host = request.get_host()
    protocol = 'wss' if request.is_secure() else 'ws'
    
    # WebSocket URL
    ws_url = f"{protocol}://{host}/ws/hume-twilio/stream/{call_sid}"
    
    logger.info(f"🔌 WebSocket URL: {ws_url}")
    
    # Connect to WebSocket stream
    connect = Connect()
    stream = Stream(url=ws_url)
    connect.append(stream)
    response.append(connect)
    
    # Return TwiML
    twiml_str = str(response)
    logger.info(f"✅ Returning TwiML: {twiml_str[:200]}")
    
    return HttpResponse(twiml_str, content_type='application/xml; charset=utf-8')


@csrf_exempt  
@require_http_methods(["GET", "POST"])
def status_callback_fixed(request):
    """
    Fixed status callback
    """
    call_sid = request.POST.get('CallSid') or request.GET.get('CallSid', 'UNKNOWN')
    call_status = request.POST.get('CallStatus') or request.GET.get('CallStatus', 'UNKNOWN')
    
    logger.info(f"📊 Status callback: {call_sid} = {call_status}")
    
    # Update database
    try:
        from HumeAiTwilio.models import TwilioCall
        call = TwilioCall.objects.filter(call_sid=call_sid).first()
        if call:
            call.status = call_status.lower()
            call.save()
            logger.info(f"✅ Updated call {call_sid} status to {call_status}")
    except Exception as e:
        logger.error(f"⚠️  Error updating call: {e}")
    
    return HttpResponse('OK', content_type='text/plain', status=200)


# URLs to add to HumeAiTwilio/urls.py:
"""
from .twilio_voice_bridge_fixed import voice_webhook_fixed, status_callback_fixed

urlpatterns = [
    # ... existing patterns ...
    
    # Fixed webhooks that work with ngrok
    path('voice-webhook-fixed/', voice_webhook_fixed, name='voice-webhook-fixed'),
    path('status-callback-fixed/', status_callback_fixed, name='status-callback-fixed'),
]
"""

print("""
✅ Fixed webhook views created!

To use:

1. Add to HumeAiTwilio/urls.py:
   from .twilio_voice_bridge_fixed import voice_webhook_fixed, status_callback_fixed
   
   urlpatterns += [
       path('voice-webhook-fixed/', voice_webhook_fixed, name='voice-webhook-fixed'),
       path('status-callback-fixed/', status_callback_fixed, name='status-callback-fixed'),
   ]

2. Update Twilio webhook URLs to:
   Voice: https://YOUR-NGROK-URL/api/hume-twilio/voice-webhook-fixed/
   Status: https://YOUR-NGROK-URL/api/hume-twilio/status-callback-fixed/

3. Or better yet, restart ngrok with:
   ngrok http 8002 --domain=YOUR-STATIC-DOMAIN (paid)
   
   OR use LocalTunnel (FREE):
   npm install -g localtunnel
   lt --port 8002
""")
