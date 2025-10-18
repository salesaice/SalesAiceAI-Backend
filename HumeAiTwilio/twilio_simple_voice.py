"""
HumeAI Twilio Integration - WITHOUT WebSocket
FREE PythonAnywhere version using HTTP Recording
"""

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from decouple import config
import requests
import json
import base64
from .models import HumeAgent, TwilioCall, ConversationLog
import uuid

# Twilio Configuration
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER')

# HumeAI Configuration
HUME_AI_API_KEY = config('HUME_AI_API_KEY')
HUME_CONFIG_ID = config('HUME_CONFIG_ID')


@csrf_exempt
def twilio_voice_webhook_simple(request):
    """
    Handle incoming calls WITHOUT WebSocket
    Uses Twilio's Record + Gather for interaction
    ✅ Works on FREE PythonAnywhere
    """
    response = VoiceResponse()
    
    # Get or create call record
    call_sid = request.POST.get('CallSid')
    from_number = request.POST.get('From')
    to_number = request.POST.get('To')
    
    # Get active agent
    try:
        agent = HumeAgent.objects.filter(is_active=True).first()
        if not agent:
            response.say("Sorry, no agent is available at the moment.")
            return HttpResponse(str(response), content_type='text/xml')
    except Exception as e:
        response.say("Sorry, there was an error. Please try again later.")
        return HttpResponse(str(response), content_type='text/xml')
    
    # Create or get call record
    call, created = TwilioCall.objects.get_or_create(
        twilio_call_sid=call_sid,
        defaults={
            'call_id': str(uuid.uuid4()),
            'agent': agent,
            'from_number': from_number,
            'to_number': to_number,
            'status': 'in-progress',
            'direction': 'inbound'
        }
    )
    
    # Initial greeting
    if created or not ConversationLog.objects.filter(call=call).exists():
        greeting = "Hello! I'm your AI assistant. How can I help you today?"
        response.say(greeting, voice='Polly.Joanna')
        
        # Log greeting
        ConversationLog.objects.create(
            call=call,
            speaker='agent',
            message=greeting,
            timestamp=0
        )
    
    # Gather user input (speech)
    gather = Gather(
        input='speech',
        action='/api/hume-twilio/process-speech-simple/',
        method='POST',
        timeout=5,
        speech_timeout='auto',
        language='en-US'
    )
    response.append(gather)
    
    # If no input, prompt again
    response.say("Are you still there?")
    response.redirect('/api/hume-twilio/voice-webhook-simple/')
    
    return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
def process_speech_simple(request):
    """
    Process user speech and get AI response
    ✅ Works WITHOUT WebSocket
    """
    response = VoiceResponse()
    
    # Get speech result
    speech_result = request.POST.get('SpeechResult', '').strip()
    call_sid = request.POST.get('CallSid')
    
    if not speech_result:
        response.say("I didn't catch that. Could you please repeat?")
        response.redirect('/api/hume-twilio/voice-webhook-simple/')
        return HttpResponse(str(response), content_type='text/xml')
    
    # Get call record
    try:
        call = TwilioCall.objects.get(twilio_call_sid=call_sid)
        agent = call.agent
    except TwilioCall.DoesNotExist:
        response.say("Sorry, there was an error. Please call again.")
        return HttpResponse(str(response), content_type='text/xml')
    
    # Log user message
    ConversationLog.objects.create(
        call=call,
        speaker='user',
        message=speech_result,
        timestamp=0
    )
    
    # Get AI response from HumeAI
    try:
        ai_response = get_hume_response_simple(speech_result, agent)
        
        # Log AI response
        ConversationLog.objects.create(
            call=call,
            speaker='agent',
            message=ai_response,
            timestamp=0
        )
        
        # Speak AI response
        response.say(ai_response, voice='Polly.Joanna')
        
    except Exception as e:
        print(f"Error getting AI response: {str(e)}")
        response.say("I'm having trouble understanding. Let me try again.")
    
    # Continue conversation
    gather = Gather(
        input='speech',
        action='/api/hume-twilio/process-speech-simple/',
        method='POST',
        timeout=5,
        speech_timeout='auto',
        language='en-US'
    )
    response.append(gather)
    
    # If no more input, end call
    response.say("Thank you for calling. Goodbye!")
    response.hangup()
    
    return HttpResponse(str(response), content_type='text/xml')


def get_hume_response_simple(user_message, agent):
    """
    Get response from HumeAI using HTTP API (not WebSocket)
    ✅ Simple text-based interaction
    """
    
    # For now, use a simple response
    # You can integrate HumeAI's HTTP API here if available
    
    # Simple AI-like responses based on keywords
    user_message_lower = user_message.lower()
    
    if 'hello' in user_message_lower or 'hi' in user_message_lower:
        return "Hello! It's great to hear from you. How can I assist you today?"
    
    elif 'help' in user_message_lower:
        return "I'm here to help! I can answer questions, provide information, or assist with your needs. What would you like to know?"
    
    elif 'product' in user_message_lower or 'service' in user_message_lower:
        return "We offer a variety of products and services. Could you tell me more about what you're interested in?"
    
    elif 'price' in user_message_lower or 'cost' in user_message_lower:
        return "I'd be happy to discuss pricing with you. Let me get some more details about what you need."
    
    elif 'thank' in user_message_lower:
        return "You're very welcome! Is there anything else I can help you with?"
    
    elif 'bye' in user_message_lower or 'goodbye' in user_message_lower:
        return "Thank you for calling! Have a wonderful day. Goodbye!"
    
    else:
        return f"I understand you said: {user_message}. Let me help you with that. Could you provide more details?"


@csrf_exempt
def twilio_status_callback_simple(request):
    """Handle call status updates"""
    call_sid = request.POST.get('CallSid')
    call_status = request.POST.get('CallStatus')
    
    try:
        call = TwilioCall.objects.get(twilio_call_sid=call_sid)
        call.status = call_status
        
        if call_status == 'completed':
            call.end_time = request.POST.get('Timestamp')
            duration = request.POST.get('CallDuration', 0)
            call.duration = int(duration)
        
        call.save()
    except TwilioCall.DoesNotExist:
        pass
    
    return HttpResponse(status=200)


def initiate_outbound_call_simple(phone_number, agent_id):
    """
    Make outbound call WITHOUT WebSocket
    ✅ Works on FREE PythonAnywhere
    """
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    # Get agent
    try:
        agent = HumeAgent.objects.get(id=agent_id)
    except HumeAgent.DoesNotExist:
        return None
    
    # Create call record
    call = TwilioCall.objects.create(
        call_id=str(uuid.uuid4()),
        agent=agent,
        from_number=TWILIO_PHONE_NUMBER,
        to_number=phone_number,
        status='initiated',
        direction='outbound'
    )
    
    # Make call
    try:
        twilio_call = client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            url='https://aicegroup.pythonanywhere.com/api/hume-twilio/voice-webhook-simple/',
            status_callback='https://aicegroup.pythonanywhere.com/api/hume-twilio/status-callback-simple/',
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST'
        )
        
        call.twilio_call_sid = twilio_call.sid
        call.save()
        
        return call
        
    except Exception as e:
        call.status = 'failed'
        call.save()
        raise e
