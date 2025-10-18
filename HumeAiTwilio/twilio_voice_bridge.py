"""
🎙️ TWILIO VOICE BRIDGE FOR HUMEAI
Complete integration for real phone call testing with HumeAI agents
"""

from twilio.twiml.voice_response import VoiceResponse, Start, Stream
from twilio.rest import Client
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decouple import config
import logging

logger = logging.getLogger(__name__)

# Twilio config
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')

# HumeAI config
HUME_API_KEY = config('HUME_API_KEY', default='')
HUME_CONFIG_ID = config('HUME_CONFIG_ID', default='')

# Your server URL (for webhooks)
SERVER_URL = config('SERVER_URL', default='http://127.0.0.1:8000')


@csrf_exempt
@require_POST
def twilio_voice_webhook(request):
    """
    Twilio Voice Webhook - Handles incoming calls
    This is called when someone calls your Twilio number
    """
    from_number = request.POST.get('From', 'Unknown')
    to_number = request.POST.get('To', 'Unknown')
    call_sid = request.POST.get('CallSid', 'Unknown')
    
    logger.info(f"📞 Incoming call: {from_number} → {to_number} (SID: {call_sid})")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Greeting message
    response.say(
        "Hello! You are now connected to our AI agent. Please wait while we connect you.",
        voice='Polly.Joanna'
    )
    
    # Start media stream to HumeAI
    start = Start()
    stream = Stream(
        url=f'wss://{request.get_host()}/api/hume-twilio/stream/{call_sid}',
        track='both_tracks'  # Capture both caller and agent audio
    )
    start.append(stream)
    response.append(start)
    
    # Keep the call alive
    response.pause(length=60)
    
    logger.info(f"✅ TwiML response generated for call {call_sid}")
    
    return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
@require_POST
def twilio_status_callback(request):
    """
    Callback for call status updates
    """
    call_sid = request.POST.get('CallSid', 'Unknown')
    call_status = request.POST.get('CallStatus', 'Unknown')
    
    logger.info(f"📊 Call {call_sid} status: {call_status}")
    
    # Update call record in database
    from .models import TwilioCall
    try:
        call = TwilioCall.objects.get(call_sid=call_sid)
        call.status = call_status.lower()
        call.save()
        logger.info(f"✅ Updated call {call_sid} status to {call_status}")
    except TwilioCall.DoesNotExist:
        logger.warning(f"⚠️ Call {call_sid} not found in database")
    
    return HttpResponse('OK', status=200)


def initiate_outbound_call(to_number, agent_id=None):
    """
    Make an outbound call using Twilio
    
    Args:
        to_number: Phone number to call (e.g., '+1234567890')
        agent_id: HumeAI agent UUID (optional)
    
    Returns:
        dict: Call details including call_sid
    """
    from .models import HumeAgent, TwilioCall
    from django.utils import timezone
    
    # Get agent
    if agent_id:
        try:
            agent = HumeAgent.objects.get(id=agent_id)
        except HumeAgent.DoesNotExist:
            agent = HumeAgent.objects.filter(status='active').first()
    else:
        agent = HumeAgent.objects.filter(status='active').first()
    
    if not agent:
        raise ValueError("No active agent found")
    
    # Initialize Twilio client
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    # Make call
    try:
        call = client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            url=f'{SERVER_URL}/api/hume-twilio/voice-webhook/',
            status_callback=f'{SERVER_URL}/api/hume-twilio/status-callback/',
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            record=True  # Record the call
        )
        
        # Create database record
        db_call = TwilioCall.objects.create(
            agent=agent,
            call_sid=call.sid,
            from_number=TWILIO_PHONE_NUMBER,
            to_number=to_number,
            status='initiated',
            direction='outbound',
            started_at=timezone.now()
        )
        
        logger.info(f"✅ Outbound call initiated: {call.sid}")
        
        return {
            'success': True,
            'call_sid': call.sid,
            'call_id': str(db_call.id),
            'agent': agent.name,
            'status': 'initiated'
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to initiate call: {e}")
        return {
            'success': False,
            'error': str(e)
        }
