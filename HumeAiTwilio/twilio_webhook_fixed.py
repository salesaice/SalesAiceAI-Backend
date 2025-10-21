"""
🔧 FIXED TWILIO WEBHOOK - Bypasses Ngrok Warning
Returns proper TwiML for Twilio calls
"""

from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from decouple import config
import logging

logger = logging.getLogger(__name__)

# Configuration
BASE_URL = config('BASE_URL', default='https://roguishly-oncogenic-amiyah.ngrok-free.dev')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def twilio_voice_webhook_fixed(request):
    """
    FIXED: Twilio Voice Webhook that returns proper TwiML
    Works with ngrok by returning XML directly
    """
    # Get Twilio parameters
    call_sid = request.POST.get('CallSid') or request.GET.get('CallSid', 'UNKNOWN')
    from_number = request.POST.get('From') or request.GET.get('From', 'Unknown')
    to_number = request.POST.get('To') or request.GET.get('To', 'Unknown')
    call_status = request.POST.get('CallStatus') or request.GET.get('CallStatus', 'unknown')
    
    logger.info(f"📞 Voice webhook called: {from_number} → {to_number} (SID: {call_sid}, Status: {call_status})")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Initial greeting
    response.say(
        "Hello! Connecting you to the A I assistant. Please wait.",
        voice='alice',
        language='en-US'
    )
    
    # Add WebSocket stream for bidirectional audio
    connect = Connect()
    
    # WebSocket URL - use wss:// for https ngrok URLs
    ws_url = BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')
    stream_url = f"{ws_url}/ws/hume-twilio/stream/{call_sid}/"
    
    logger.info(f"🔌 WebSocket URL: {stream_url}")
    
    stream = Stream(url=stream_url)
    connect.append(stream)
    response.append(connect)
    
    # Keep call alive
    response.pause(length=300)  # 5 minutes
    
    # Convert to XML string
    twiml_xml = str(response)
    
    logger.info(f"✅ Returning TwiML for call {call_sid}")
    logger.debug(f"TwiML: {twiml_xml}")
    
    # Return with proper XML content type
    return HttpResponse(twiml_xml, content_type='application/xml')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def twilio_status_callback_fixed(request):
    """
    FIXED: Status callback that always returns 200 OK
    """
    call_sid = request.POST.get('CallSid') or request.GET.get('CallSid', 'UNKNOWN')
    call_status = request.POST.get('CallStatus') or request.GET.get('CallStatus', 'unknown')
    
    logger.info(f"📊 Status callback: {call_sid} → {call_status}")
    
    # Update database if call exists
    try:
        from .models import TwilioCall
        call = TwilioCall.objects.filter(call_sid=call_sid).first()
        if call:
            call.status = call_status.lower().replace('-', '_')
            call.save()
            logger.info(f"✅ Updated call {call_sid} status to {call_status}")
    except Exception as e:
        logger.warning(f"⚠️  Could not update call: {e}")
    
    # Always return 200 OK with XML
    return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', 
                       content_type='application/xml')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def health_check(request):
    """
    Simple health check endpoint
    """
    return HttpResponse('OK', status=200)
