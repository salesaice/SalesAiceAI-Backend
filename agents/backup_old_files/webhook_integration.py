from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import models
import json
import logging
from .real_time_learning import RealTimeCallLearningAPIView
from .ai_agent_models import AIAgent, CallSession

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])  
def hume_ai_webhook(request):
    """
    HumeAI webhook endpoint
    Jab HumeAI mein koi event hota hai, ye automatically call hoti hai
    """
    try:
        data = json.loads(request.body)
        event_type = data.get('event_type')
        conversation_id = data.get('conversation_id')
        
        # Find the corresponding call session
        try:
            call_session = CallSession.objects.get(
                twilio_call_sid=conversation_id
            )
            agent = call_session.ai_agent
        except CallSession.DoesNotExist:
            logger.error(f"Call session not found for conversation: {conversation_id}")
            return JsonResponse({'status': 'error', 'message': 'Call session not found'})
        
        # Process different HumeAI events
        if event_type == 'customer_objection_detected':
            # Customer ne objection diya
            learning_data = {
                'call_id': str(call_session.id),
                'learning_event': 'customer_objection',
                'objection_text': data.get('objection_text', ''),
                'agent_response': data.get('agent_response', ''),
                'effectiveness_score': data.get('customer_engagement_score', 5),
                'customer_reaction': data.get('customer_sentiment_after', 'neutral')
            }
            
            # Call real-time learning
            learning_view = RealTimeCallLearningAPIView()
            learning_view.request = type('MockRequest', (), {
                'user': call_session.ai_agent.client,
                'data': learning_data
            })()
            learning_view.post(learning_view.request)
            
        elif event_type == 'sentiment_change_detected':
            # Customer ka mood change hua
            learning_data = {
                'call_id': str(call_session.id),
                'learning_event': 'call_sentiment_change',
                'previous_sentiment': data.get('previous_sentiment', 'neutral'),
                'current_sentiment': data.get('current_sentiment', 'neutral'),
                'trigger_action': data.get('agent_last_response', ''),
                'sentiment_score': data.get('sentiment_score_change', 0)
            }
            
            learning_view = RealTimeCallLearningAPIView()
            learning_view.request = type('MockRequest', (), {
                'user': agent.client,
                'data': learning_data
            })()
            learning_view.post(learning_view.request)
            
        elif event_type == 'successful_response_detected':
            # Agent ka response successful raha
            learning_data = {
                'call_id': str(call_session.id),
                'learning_event': 'successful_response',
                'approach_used': data.get('agent_response', ''),
                'context': data.get('conversation_context', ''),
                'customer_reaction': data.get('customer_positive_reaction', ''),
                'effectiveness_score': data.get('effectiveness_score', 8)
            }
            
            learning_view = RealTimeCallLearningAPIView()
            learning_view.request = type('MockRequest', (), {
                'user': agent.client,
                'data': learning_data
            })()
            learning_view.post(learning_view.request)
            
        elif event_type == 'conversation_ended':
            # Call khatam ho gayi - comprehensive analysis
            from .real_time_learning import AutoCallAnalysisAPIView
            
            analysis_data = {
                'call_id': str(call_session.id),
                'conversation_id': conversation_id,
                'full_transcript': data.get('full_transcript', ''),
                'customer_satisfaction': data.get('customer_satisfaction_score', 5)
            }
            
            analysis_view = AutoCallAnalysisAPIView()
            analysis_view.request = type('MockRequest', (), {
                'user': agent.client,
                'data': analysis_data
            })()
            analysis_view.post(analysis_view.request)
        
        logger.info(f"Processed HumeAI webhook event: {event_type}")
        return JsonResponse({'status': 'success', 'event_processed': event_type})
        
    except Exception as e:
        logger.error(f"HumeAI webhook error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt 
@require_http_methods(["POST"])
def twilio_webhook(request):
    """
    Twilio webhook for call events
    Twilio call events par learning trigger karna
    """
    try:
        # Twilio sends form data, not JSON
        event = request.POST.get('CallStatus')
        call_sid = request.POST.get('CallSid')
        
        if event == 'completed':
            # Call completed - trigger final analysis
            try:
                call_session = CallSession.objects.get(twilio_call_sid=call_sid)
                
                # Mark call as ended
                call_session.ended_at = timezone.now()
                if call_session.connected_at:
                    duration = (call_session.ended_at - call_session.connected_at).total_seconds()
                    call_session.duration_seconds = int(duration)
                call_session.save()
                
                # Trigger automatic learning if we have HumeAI data
                if hasattr(call_session, 'hume_conversation_id'):
                    # This would typically trigger HumeAI analysis
                    # Which would then call our webhook above
                    pass
                
            except CallSession.DoesNotExist:
                logger.error(f"Call session not found for Twilio SID: {call_sid}")
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Twilio webhook error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt 
@require_http_methods(["POST"])
def twilio_voice_webhook(request):
    """
    Twilio Voice webhook - handles incoming/outgoing call initiation
    """
    try:
        from_number = request.POST.get('From', '')
        to_number = request.POST.get('To', '')
        call_sid = request.POST.get('CallSid', '')
        
        # Find or create call session
        try:
            call_session = CallSession.objects.get(twilio_call_sid=call_sid)
        except CallSession.DoesNotExist:
            # This might be an inbound call - create new session
            # You'd typically have logic here to find the appropriate agent
            logger.info(f"New inbound call from {from_number} to {to_number}")
        
        # Return TwiML response to connect to HumeAI
        twiml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Please hold while I connect you to our AI assistant.</Say>
    <Connect>
        <Stream url="wss://api.hume.ai/v0/evi/chat" />
    </Connect>
    <Say voice="Polly.Joanna">Thank you for calling. Have a great day!</Say>
</Response>'''
        
        return HttpResponse(twiml_response, content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Twilio voice webhook error: {str(e)}")
        # Return basic TwiML response
        return HttpResponse('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">I'm sorry, there was a technical issue. Please try again later.</Say>
</Response>''', content_type='text/xml')


@csrf_exempt
@require_http_methods(["POST"])
def twilio_status_webhook(request):
    """
    Twilio Status webhook - tracks call progress and completion
    """
    try:
        call_sid = request.POST.get('CallSid', '')
        call_status = request.POST.get('CallStatus', '')
        call_duration = request.POST.get('CallDuration', '0')
        recording_url = request.POST.get('RecordingUrl', '')
        
        logger.info(f"Twilio status update: {call_sid} - {call_status}")
        
        # Update call session status
        try:
            call_session = CallSession.objects.get(twilio_call_sid=call_sid)
            
            if call_status == 'in-progress' and not call_session.connected_at:
                call_session.connected_at = timezone.now()
                
            elif call_status == 'completed':
                call_session.ended_at = timezone.now()
                call_session.duration_seconds = int(call_duration) if call_duration.isdigit() else 0
                
                # Set outcome based on duration
                if call_session.duration_seconds > 60:  # More than 1 minute
                    call_session.outcome = 'answered'
                else:
                    call_session.outcome = 'no_answer'
                
                # Save recording URL if available
                if recording_url:
                    if not call_session.agent_notes:
                        call_session.agent_notes = {}
                    call_session.agent_notes['recording_url'] = recording_url
            
            elif call_status in ['busy', 'no-answer', 'failed']:
                call_session.outcome = call_status.replace('-', '_')
                call_session.ended_at = timezone.now()
            
            call_session.save()
            
            # Trigger automatic learning for completed calls
            if call_status == 'completed' and call_session.duration_seconds > 30:
                # Basic learning data from call metadata
                learning_data = {
                    'call_id': str(call_session.id),
                    'learning_event': 'call_completed',
                    'call_duration': call_session.duration_seconds,
                    'call_outcome': call_session.outcome,
                    'automated_learning': True
                }
                
                # Trigger basic learning
                learning_view = RealTimeCallLearningAPIView()
                mock_request = type('MockRequest', (), {
                    'user': call_session.ai_agent.client,
                    'data': learning_data
                })()
                learning_view.post(mock_request)
            
        except CallSession.DoesNotExist:
            logger.warning(f"Call session not found for Twilio SID: {call_sid}")
        
        return JsonResponse({'status': 'success', 'call_status': call_status})
        
    except Exception as e:
        logger.error(f"Twilio status webhook error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


# Manual trigger for testing
@csrf_exempt
@require_http_methods(["POST"])
def manual_learning_trigger(request):
    """
    Manual learning trigger for testing/debugging
    Testing ke liye manual trigger
    """
    try:
        data = json.loads(request.body)
        call_id = data.get('call_id')
        
        call_session = CallSession.objects.get(id=call_id)
        agent = call_session.ai_agent
        
        # Simulate learning events for testing
        learning_events = [
            {
                'learning_event': 'customer_objection',
                'objection_text': 'This is too expensive',
                'agent_response': 'I understand, let me show you the value',
                'effectiveness_score': 7,
                'customer_reaction': 'interested'
            },
            {
                'learning_event': 'successful_response', 
                'approach_used': 'Explained ROI with specific numbers',
                'context': 'Price objection',
                'customer_reaction': 'Asked follow-up questions',
                'effectiveness_score': 9
            }
        ]
        
        for event_data in learning_events:
            event_data['call_id'] = call_id
            
            learning_view = RealTimeCallLearningAPIView()
            learning_view.request = type('MockRequest', (), {
                'user': agent.client,
                'data': event_data
            })()
            result = learning_view.post(learning_view.request)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Processed {len(learning_events)} learning events',
            'call_id': call_id
        })
        
    except Exception as e:
        logger.error(f"Manual learning trigger error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})
