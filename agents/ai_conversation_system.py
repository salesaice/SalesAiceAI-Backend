from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
import logging
import requests
from django.conf import settings

from .ai_agent_models import AIAgent, CallSession, CustomerProfile
from .ai_training_views import ai_agent_learning

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def hume_ai_webhook(request):
    """
    HumeAI Webhook for real-time emotional intelligence
    HumeAI se emotional data receive karta hai calls ke dauraan
    """
    try:
        webhook_data = request.data
        logger.info(f"HumeAI webhook received: {webhook_data}")
        
        # Extract conversation data from HumeAI
        conversation_id = webhook_data.get('conversation_id')
        emotions = webhook_data.get('emotions', {})
        sentiment_analysis = webhook_data.get('sentiment', {})
        conversation_events = webhook_data.get('events', [])
        
        if not conversation_id:
            return Response({'error': 'Missing conversation_id'}, status=400)
        
        # Find associated call session
        try:
            call_session = CallSession.objects.get(hume_conversation_id=conversation_id)
            agent = call_session.ai_agent
        except CallSession.DoesNotExist:
            logger.warning(f"No call session found for HumeAI conversation: {conversation_id}")
            return Response({'status': 'no_session_found'}, status=200)
        
        # Process emotional intelligence data
        processed_emotions = {
            'primary_emotion': emotions.get('primary', 'neutral'),
            'emotion_confidence': emotions.get('confidence', 0),
            'sentiment_score': sentiment_analysis.get('score', 0),
            'sentiment_magnitude': sentiment_analysis.get('magnitude', 0),
            'emotional_journey': emotions.get('timeline', [])
        }
        
        # Update call session with HumeAI data
        call_session.customer_sentiment = processed_emotions
        
        # Process conversation events for learning
        learning_events = []
        for event in conversation_events:
            if event.get('type') == 'customer_response':
                learning_events.append({
                    'timestamp': event.get('timestamp'),
                    'customer_text': event.get('text', ''),
                    'emotion_detected': event.get('emotion', 'neutral'),
                    'confidence': event.get('confidence', 0)
                })
            elif event.get('type') == 'agent_response':
                learning_events.append({
                    'timestamp': event.get('timestamp'), 
                    'agent_text': event.get('text', ''),
                    'effectiveness': event.get('effectiveness', 0)
                })
        
        # Real-time learning during call
        if learning_events:
            # Extract customer responses and agent effectiveness
            customer_responses = [
                event['customer_text'] for event in learning_events 
                if event.get('customer_text')
            ]
            
            # Determine call progress and sentiment changes
            emotional_progression = []
            for event in learning_events:
                if event.get('emotion_detected'):
                    emotional_progression.append({
                        'emotion': event['emotion_detected'],
                        'timestamp': event.get('timestamp'),
                        'confidence': event.get('confidence', 0)
                    })
            
            # Calculate emotional improvement during call
            if len(emotional_progression) >= 2:
                initial_emotion = emotional_progression[0]['emotion']
                current_emotion = emotional_progression[-1]['emotion']
                
                positive_emotions = ['joy', 'satisfaction', 'interest', 'curiosity']
                negative_emotions = ['anger', 'frustration', 'boredom', 'disappointment']
                
                emotion_improved = (
                    initial_emotion in negative_emotions and current_emotion in positive_emotions
                ) or (
                    current_emotion in positive_emotions and initial_emotion not in positive_emotions
                )
                
                # Real-time learning if emotion improved
                if emotion_improved:
                    recent_agent_responses = [
                        event.get('agent_text', '') for event in learning_events[-3:]
                        if event.get('agent_text')
                    ]
                    
                    if recent_agent_responses:
                        # Trigger real-time learning
                        learning_data = {
                            'call_outcome': 'interested',
                            'customer_satisfaction': 7 if current_emotion in positive_emotions else 5,
                            'customer_responses': customer_responses[-3:],
                            'agent_performance_notes': f"Emotional improvement detected: {initial_emotion} -> {current_emotion}. Effective responses: {' | '.join(recent_agent_responses[-2:])}",
                            'successful_techniques': ['emotional_intelligence', 'adaptive_response'],
                            'call_duration': call_session.duration_seconds or 0
                        }
                        
                        # Apply learning to agent
                        agent.update_learning_data({
                            'successful': True,
                            'outcome': 'emotional_improvement',
                            'satisfaction': 7,
                            'customer_response': ' '.join(customer_responses[-2:]),
                            'notes': f"HumeAI detected emotional improvement: {initial_emotion} -> {current_emotion}",
                            'call_duration': call_session.duration_seconds or 0,
                            'customer_interest_level': 'warm'
                        })
        
        # Store processed data
        call_session.agent_performance = {
            'hume_analysis': processed_emotions,
            'conversation_events': learning_events,
            'emotional_intelligence_applied': True,
            'real_time_learning': len(learning_events) > 0
        }
        
        call_session.save()
        
        # Generate real-time insights for agent
        insights = []
        if processed_emotions['primary_emotion'] in ['anger', 'frustration']:
            insights.append({
                'type': 'emotion_alert',
                'message': 'Customer showing frustration - try empathetic approach',
                'urgency': 'high'
            })
        elif processed_emotions['primary_emotion'] in ['interest', 'curiosity']:
            insights.append({
                'type': 'opportunity',
                'message': 'Customer showing interest - good time to present benefits',
                'urgency': 'medium'
            })
        
        return Response({
            'status': 'processed',
            'conversation_id': conversation_id,
            'emotional_analysis': processed_emotions,
            'learning_applied': len(learning_events) > 0,
            'real_time_insights': insights,
            'call_session_updated': True
        }, status=200)
        
    except Exception as e:
        logger.error(f"HumeAI webhook processing error: {str(e)}")
        return Response({'error': str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def twilio_voice_webhook(request):
    """
    Twilio Voice Webhook for call events
    Twilio se call events receive karta hai
    """
    try:
        webhook_data = request.data
        logger.info(f"Twilio voice webhook received: {webhook_data}")
        
        call_sid = webhook_data.get('CallSid')
        call_status = webhook_data.get('CallStatus')
        from_number = webhook_data.get('From')
        to_number = webhook_data.get('To')
        
        if not call_sid:
            return Response({'error': 'Missing CallSid'}, status=400)
        
        # Find or create call session
        call_session, created = CallSession.objects.get_or_create(
            twilio_call_sid=call_sid,
            defaults={
                'phone_number': from_number or to_number,
                'call_type': 'inbound' if from_number else 'outbound',
                'outcome': 'answered'
            }
        )
        
        # Update call status
        if call_status == 'completed':
            call_session.ended_at = timezone.now()
            duration = webhook_data.get('CallDuration')
            if duration:
                call_session.duration_seconds = int(duration)
        elif call_status == 'busy':
            call_session.outcome = 'busy'
        elif call_status == 'no-answer':
            call_session.outcome = 'voicemail'
        
        call_session.save()
        
        return Response({
            'status': 'processed',
            'call_sid': call_sid,
            'call_status': call_status,
            'session_updated': True
        }, status=200)
        
    except Exception as e:
        logger.error(f"Twilio voice webhook error: {str(e)}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def start_ai_call(request):
    """
    Start AI-powered call with HumeAI integration
    HumeAI ke saath AI call start karta hai
    """
    try:
        phone_number = request.data.get('phone_number')
        agent_id = request.data.get('agent_id')
        call_context = request.data.get('context', {})
        
        if not phone_number or not agent_id:
            return Response({
                'error': 'Missing required fields',
                'required': ['phone_number', 'agent_id']
            }, status=400)
        
        # Get AI agent
        try:
            agent = AIAgent.objects.get(id=agent_id)
        except AIAgent.DoesNotExist:
            return Response({'error': 'AI Agent not found'}, status=404)
        
        if not agent.is_ready_for_calls:
            return Response({
                'error': 'Agent not ready for calls',
                'training_level': agent.training_level,
                'message': 'Complete agent training first'
            }, status=400)
        
        # Get or create customer profile
        customer_profile, created = CustomerProfile.objects.get_or_create(
            ai_agent=agent,
            phone_number=phone_number,
            defaults={
                'interest_level': 'cold',
                'communication_style': 'friendly'
            }
        )
        
        # Create call session
        call_session = CallSession.objects.create(
            ai_agent=agent,
            customer_profile=customer_profile,
            phone_number=phone_number,
            call_type='outbound',
            outcome='answered'
        )
        
        # Initialize HumeAI conversation
        hume_conversation_id = None
        try:
            hume_api_key = getattr(settings, 'HUME_AI_API_KEY', '')
            if hume_api_key:
                hume_response = requests.post(
                    'https://api.hume.ai/v0/batch/conversations',
                    headers={
                        'X-Hume-Api-Key': hume_api_key,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'call_metadata': {
                            'call_session_id': str(call_session.id),
                            'customer_phone': phone_number,
                            'agent_name': agent.name
                        }
                    }
                )
                
                if hume_response.status_code == 201:
                    hume_data = hume_response.json()
                    hume_conversation_id = hume_data.get('conversation_id')
                    call_session.hume_conversation_id = hume_conversation_id
                    call_session.save()
        except Exception as e:
            logger.warning(f"HumeAI initialization failed: {str(e)}")
        
        # Initiate Twilio call
        from .twilio_service import TwilioCallService
        twilio_service = TwilioCallService()
        
        # Prepare agent configuration for call
        agent_config = {
            'agent_id': str(agent.id),
            'agent_name': agent.name,
            'personality_type': agent.personality_type,
            'sales_script': agent.conversation_memory.get('sales_script', ''),
            'objection_responses': agent.conversation_memory.get('objection_responses', {}),
            'hume_conversation_id': hume_conversation_id,
            'customer_profile': {
                'interest_level': customer_profile.interest_level,
                'communication_style': customer_profile.communication_style,
                'previous_calls': customer_profile.total_calls
            }
        }
        
        call_result = twilio_service.initiate_call(
            to=phone_number,
            agent_config=agent_config,
            call_context=call_context
        )
        
        # Update call session with Twilio data
        if call_result.get('call_sid'):
            call_session.twilio_call_sid = call_result['call_sid']
            call_session.save()
        
        return Response({
            'status': 'call_initiated',
            'call_session_id': str(call_session.id),
            'twilio_call_sid': call_result.get('call_sid'),
            'hume_conversation_id': hume_conversation_id,
            'agent_info': {
                'name': agent.name,
                'training_level': agent.training_level,
                'personality_type': agent.personality_type
            },
            'customer_info': {
                'interest_level': customer_profile.interest_level,
                'previous_calls': customer_profile.total_calls,
                'is_new_customer': created
            },
            'call_capabilities': {
                'hume_ai_enabled': bool(hume_conversation_id),
                'real_time_learning': True,
                'emotional_intelligence': bool(hume_conversation_id),
                'adaptive_responses': True
            }
        }, status=201)
        
    except Exception as e:
        logger.error(f"AI call initiation error: {str(e)}")
        return Response({
            'error': 'Call initiation failed',
            'message': str(e)
        }, status=500)


@api_view(['POST'])
def complete_ai_call(request):
    """
    Complete AI call and trigger comprehensive learning
    Call complete hone par comprehensive learning
    """
    try:
        call_session_id = request.data.get('call_session_id')
        final_outcome = request.data.get('final_outcome')
        conversation_transcript = request.data.get('conversation_transcript', '')
        customer_feedback = request.data.get('customer_feedback', {})
        
        if not call_session_id:
            return Response({'error': 'Missing call_session_id'}, status=400)
        
        # Get call session
        call_session = CallSession.objects.get(id=call_session_id)
        agent = call_session.ai_agent
        customer_profile = call_session.customer_profile
        
        # Update call session
        call_session.outcome = final_outcome or 'completed'
        call_session.ended_at = timezone.now()
        call_session.conversation_transcript = conversation_transcript
        
        # Calculate duration if not set
        if not call_session.duration_seconds and call_session.initiated_at:
            duration = (timezone.now() - call_session.initiated_at).total_seconds()
            call_session.duration_seconds = int(duration)
        
        call_session.save()
        
        # Update customer profile
        customer_profile.total_calls += 1
        customer_profile.last_interaction = timezone.now()
        
        # Update interest level based on call outcome
        if final_outcome == 'converted':
            customer_profile.interest_level = 'converted'
            customer_profile.is_converted = True
            customer_profile.conversion_date = timezone.now()
            customer_profile.successful_calls += 1
        elif final_outcome in ['interested', 'callback_requested']:
            if customer_profile.interest_level == 'cold':
                customer_profile.interest_level = 'warm'
            elif customer_profile.interest_level == 'warm':
                customer_profile.interest_level = 'hot'
        elif final_outcome == 'do_not_call':
            customer_profile.is_do_not_call = True
        
        customer_profile.save()
        
        # Comprehensive learning from complete call
        satisfaction_score = customer_feedback.get('satisfaction', 5)
        
        comprehensive_learning_data = {
            'call_outcome': final_outcome,
            'customer_satisfaction': satisfaction_score,
            'conversation_transcript': conversation_transcript,
            'customer_responses': [
                line.strip() for line in conversation_transcript.split('\\n')
                if line.strip() and not line.startswith('Agent:')
            ],
            'agent_performance_notes': f"Call completed with outcome: {final_outcome}. Duration: {call_session.duration_formatted}",
            'call_duration': call_session.duration_seconds,
            'objections_encountered': customer_feedback.get('objections', []),
            'successful_techniques': customer_feedback.get('successful_techniques', [])
        }
        
        # Process learning via existing endpoint
        learning_response = ai_agent_learning(request._request if hasattr(request, '_request') else request)
        
        return Response({
            'status': 'call_completed',
            'call_session_id': str(call_session.id),
            'final_outcome': final_outcome,
            'learning_applied': True,
            'customer_updated': True,
            'agent_performance': {
                'calls_handled': agent.calls_handled,
                'conversion_rate': agent.conversion_rate,
                'training_level': agent.training_level
            },
            'customer_journey': {
                'interest_level': customer_profile.interest_level,
                'total_calls': customer_profile.total_calls,
                'is_converted': customer_profile.is_converted
            },
            'next_steps': {
                'follow_up_recommended': final_outcome in ['interested', 'callback_requested'],
                'training_suggestions': [] if agent.training_level >= 80 else ['Add more objection responses', 'Improve closing techniques']
            }
        }, status=200)
        
    except CallSession.DoesNotExist:
        return Response({'error': 'Call session not found'}, status=404)
    except Exception as e:
        logger.error(f"AI call completion error: {str(e)}")
        return Response({
            'error': 'Call completion failed',
            'message': str(e)
        }, status=500)