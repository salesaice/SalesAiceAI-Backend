from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json
import time

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

from .models import CallSession, CallQueue, QuickAction
from agents.models import Agent

User = get_user_model()


class CallSessionsAPIView(APIView):
    """Manage call sessions"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: "List of call sessions",
            401: "Unauthorized"
        },
        operation_description="Get call sessions for the current user/agent",
        tags=['Calls'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        user = request.user
        
        if user.role == 'admin':
            # Admin can see all calls
            calls = CallSession.objects.all().order_by('-started_at')[:50]
        elif user.role == 'agent':
            # Agent can see their own calls
            try:
                agent = user.agent_profile
                calls = CallSession.objects.filter(agent=agent).order_by('-started_at')[:50]
            except Agent.DoesNotExist:
                calls = CallSession.objects.none()
        else:
            # User can see their own calls
            calls = CallSession.objects.filter(user=user).order_by('-started_at')[:50]
        
        data = []
        for call in calls:
            call_data = {
                'id': str(call.id),
                'call_type': call.call_type,
                'caller_number': call.caller_number,
                'callee_number': call.callee_number,
                'status': call.status,
                'started_at': call.started_at.isoformat(),
                'ended_at': call.ended_at.isoformat() if call.ended_at else None,
                'duration': call.call_duration_formatted,
                'recording_url': call.twilio_recording_url,
                'user': {
                    'id': str(call.user.id),
                    'name': call.user.get_full_name(),
                    'email': call.user.email
                } if call.user else None,
                'agent': {
                    'id': str(call.agent.id),
                    'name': call.agent.name,
                    'type': call.agent.agent_type
                } if call.agent else None,
                'ai_summary': call.ai_summary,
                'ai_sentiment': call.ai_sentiment,
                'ai_keywords': call.ai_keywords,
                'notes': call.notes
            }
            data.append(call_data)
        
        return Response({'calls': data}, status=status.HTTP_200_OK)


class CallQueueAPIView(APIView):
    """Manage call queue"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: "Current call queue",
            401: "Unauthorized"
        },
        operation_description="Get current call queue status",
        tags=['Calls'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        # Get waiting calls
        queued_calls = CallQueue.objects.filter(status='waiting').order_by('created_at')
        
        # Get available agents
        available_agents = Agent.objects.filter(
            status='available',
            is_active=True
        ).count()
        
        queue_data = []
        for queue_item in queued_calls:
            queue_data.append({
                'id': str(queue_item.id),
                'phone_number': queue_item.phone_number,
                'priority': queue_item.priority,
                'wait_time': queue_item.wait_time_minutes,
                'created_at': queue_item.created_at.isoformat(),
                'estimated_wait': queue_item.estimated_wait_time
            })
        
        return Response({
            'queue': queue_data,
            'queue_length': len(queue_data),
            'available_agents': available_agents,
            'average_wait_time': sum(item['wait_time'] for item in queue_data) / len(queue_data) if queue_data else 0
        }, status=status.HTTP_200_OK)


class StartCallAPIView(APIView):
    """Start a new call session"""
    permission_classes = [permissions.AllowAny]  # Remove authentication for testing
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number to call (must be entered)'),
                'agent_id': openapi.Schema(type=openapi.TYPE_STRING, description='Agent ID who will initiate the call'),
                'receiver_name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of the person being called (optional)'),
                'call_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of call', default='outbound'),
                'priority': openapi.Schema(type=openapi.TYPE_STRING, description='Call priority (low/medium/high)', default='medium')
            },
            required=['phone_number', 'agent_id']
        ),
        responses={
            201: "Call initiated successfully",
            400: "Bad request - missing parameters or invalid agent",
            401: "Unauthorized",
            404: "Agent not found"
        },
        operation_description="Start a new outbound call with specified agent",
        tags=['Calls'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        # Get required parameters
        phone_number = request.data.get('phone_number')
        agent_id = request.data.get('agent_id')
        receiver_name = request.data.get('receiver_name', '')  # Optional
        call_type = request.data.get('call_type', 'outbound')
        priority = request.data.get('priority', 'medium')
        
        # Validate required parameters
        if not phone_number:
            return Response({
                'error': 'Phone number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not agent_id:
            return Response({
                'error': 'Agent ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate and get the specified agent with enhanced validation
        from .agent_validation_helper import get_user_agent_for_call
        
        selected_agent = get_user_agent_for_call(request.user, agent_id)
        
        if not selected_agent:
            # List available agents for user
            from .agent_validation_helper import list_user_agents
            available_agents = list_user_agents(request.user)
            
            agent_list = []
            for agent in available_agents:
                agent_list.append({
                    'id': str(agent.id),
                    'name': agent.name,
                    'type': agent.agent_type,
                    'status': agent.status,
                    'active': agent.is_active
                })
            
            return Response({
                'error': f'Agent not found with ID: {agent_id}',
                'available_agents': agent_list,
                'suggestion': 'Please use one of the available agent IDs or create a new agent'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if agent can handle outbound calls
        if selected_agent.agent_type not in ['outbound', 'both']:
            return Response({
                'error': f'Agent "{selected_agent.name}" is not configured for outbound calls (Type: {selected_agent.agent_type})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if agent is available
        if selected_agent.status not in ['available', 'active']:
            return Response({
                'error': f'Agent is currently {selected_agent.status} and cannot initiate calls'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create call session
        call_session = CallSession.objects.create(
            user=request.user,
            caller_number='+12295152040',  # Our Twilio number (caller)
            callee_number=phone_number,   # Customer's number (who we're calling)
            caller_name=receiver_name if receiver_name else '',  # Fixed: Use empty string instead of None
            call_type=call_type,
            status='initiated',
            agent=selected_agent
        )
        
        try:
            # Update agent status to busy
            selected_agent.status = 'on_call'
            selected_agent.save()
            
            # COMPLETE AUTO VOICE INTEGRATION
            # Import auto voice system
            from .auto_voice_integration import auto_voice_system
            
            # Start complete auto voice call with Hume AI
            auto_voice_result = auto_voice_system.start_complete_auto_call(
                user=request.user,
                phone_number=phone_number,
                agent_id=str(selected_agent.id),
                call_context={
                    'call_type': call_type,
                    'priority': priority,
                    'initiated_via': 'start_call_api',
                    'user_id': str(request.user.id),
                    'receiver_name': receiver_name  # Include receiver_name in context
                }
            )
            
            if auto_voice_result.get('success'):
                # Auto voice system succeeded
                call_session.twilio_call_sid = auto_voice_result.get('twilio_call_sid')
                call_session.status = 'connecting'
                call_session.started_at = timezone.now()
                
                # Add auto voice integration data to notes
                integration_data = {
                    "auto_voice_system": True,
                    "hume_session_id": auto_voice_result.get('hume_session_id'),
                    "twilio_call_sid": auto_voice_result.get('twilio_call_sid'),
                    "agent_voice_config": {
                        "voice_tone": selected_agent.voice_tone,
                        "voice_model": getattr(selected_agent, 'voice_model', 'en-US-female-1')
                    }
                }
                call_session.notes = f"Auto Voice Integration: {json.dumps(integration_data)}"
                call_session.save()
                
                # Broadcast real-time update
                from .broadcasting import CallsBroadcaster
                broadcaster = CallsBroadcaster()
                broadcaster.broadcast_call_created(
                    call_session=call_session,
                    user_id=request.user.id,
                    agent_id=selected_agent.id
                )
                
                return Response({
                    'success': True,
                    'message': 'Auto voice call initiated successfully with AI agent',
                    'call_data': {
                        'call_id': str(call_session.id),
                        'phone_number': phone_number,
                        'receiver_name': receiver_name,
                        'status': call_session.status,
                        'twilio_call_sid': auto_voice_result.get('twilio_call_sid'),
                        'hume_session_id': auto_voice_result.get('hume_session_id'),
                        'agent': {
                            'id': str(selected_agent.id),
                            'name': selected_agent.name,
                            'type': selected_agent.agent_type,
                            'voice_tone': selected_agent.voice_tone,
                            'voice_model': getattr(selected_agent, 'voice_model', 'en-US-female-1')
                        },
                        'auto_features': auto_voice_result.get('auto_features', []),
                        'integrations': auto_voice_result.get('integrations', {}),
                        'estimated_connection_time': auto_voice_result.get('estimated_connection_time'),
                        'initiated_at': call_session.started_at.isoformat() if call_session.started_at else None
                    }
                }, status=status.HTTP_201_CREATED)
            
            else:
                # Auto voice system failed, fallback to basic Twilio
                print("⚠️ Auto voice system failed, using fallback Twilio service")
                
                # Fallback to basic Twilio service
                from agents.twilio_service import TwilioCallService
                twilio_service = TwilioCallService()
                
                # Prepare agent configuration for fallback
                agent_config = {
                    'agent_id': str(selected_agent.id),
                    'name': selected_agent.name,
                    'voice_tone': selected_agent.voice_tone,
                    'greeting': f"Hello {receiver_name if receiver_name else ''}! This is {selected_agent.name} calling.",
                    'personality': selected_agent.voice_tone,
                    'business_knowledge': selected_agent.business_knowledge.exists()
                }
                
                # Call context for personalization
                call_context = {
                    'receiver_name': receiver_name,
                    'call_purpose': 'outbound_sales',
                    'user_id': str(request.user.id),
                    'call_session_id': str(call_session.id)
                }
                
                # Initiate the call through basic Twilio
                call_result = twilio_service.initiate_call(
                    to=phone_number,
                    agent_config=agent_config,
                    call_context=call_context
                )
                
                # Update call session with Twilio data
                if call_result.get('call_sid'):
                    call_session.twilio_call_sid = call_result['call_sid']
                    call_session.status = 'connecting'
                    call_session.started_at = timezone.now()
                else:
                    call_session.status = 'failed'
                    selected_agent.status = 'available'
                    selected_agent.save()
                
                call_session.save()
                
                # Broadcast real-time update
                from .broadcasting import CallsBroadcaster
                broadcaster = CallsBroadcaster()
                broadcaster.broadcast_call_created(
                    call_session=call_session,
                    user_id=request.user.id,
                    agent_id=selected_agent.id
                )
                
                return Response({
                    'success': True,
                    'message': 'Call initiated successfully (fallback mode)',
                    'call_data': {
                        'call_id': str(call_session.id),
                        'phone_number': phone_number,
                        'receiver_name': receiver_name,
                        'status': call_session.status,
                        'twilio_call_sid': call_result.get('call_sid', 'Mock Call'),
                        'agent': {
                            'id': str(selected_agent.id),
                            'name': selected_agent.name,
                            'type': selected_agent.agent_type,
                            'voice_tone': selected_agent.voice_tone
                        },
                        'call_result': call_result,
                        'fallback_mode': True,
                        'initiated_at': call_session.started_at.isoformat() if call_session.started_at else None
                    }
                }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Rollback agent status on error
            selected_agent.status = 'available'
            selected_agent.save()
            
            # Update call session status
            call_session.status = 'failed'
            call_session.save()
            
            return Response({
                'success': False,
                'error': f'Failed to initiate call: {str(e)}',
                'call_id': str(call_session.id)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TwilioWebhookAPIView(APIView):
    """Handle Twilio webhooks for call events"""
    permission_classes = []  # Twilio webhooks don't need authentication
    
    def post(self, request):
        """Handle Twilio webhooks for both inbound and outbound calls"""
        call_sid = request.data.get('CallSid')
        call_status = request.data.get('CallStatus')
        from_number = request.data.get('From')
        to_number = request.data.get('To')
        direction = request.data.get('Direction', 'inbound')
        
        print(f"🔔 Twilio Webhook: {call_sid} - Status: {call_status} - Direction: {direction}")
        
        # Handle call based on status
        if call_status in ['ringing', 'in-progress', None]:
            # Call is connecting or active - provide TwiML response
            return self._handle_active_call(request, call_sid, from_number, to_number, direction)
        else:
            # Call status update (answered, completed, failed, etc.)
            return self._handle_status_update(request, call_sid, call_status)
    
    def _handle_active_call(self, request, call_sid, from_number, to_number, direction):
        """Handle active call and provide TwiML response with AUTO VOICE INTEGRATION"""
        try:
            # Try to find existing call session
            call_session = CallSession.objects.filter(twilio_call_sid=call_sid).first()
            
            # Check if this is an auto voice call
            if call_session and call_session.notes and "Auto Voice Integration" in call_session.notes:
                # AUTO VOICE CALL - Route to auto voice webhook
                print(f"🎭 Auto voice call detected: {call_sid}")
                
                # Import auto voice integration
                from .auto_voice_integration import AutoVoiceWebhookView
                
                # Create auto voice webhook view instance and handle request
                auto_voice_webhook = AutoVoiceWebhookView()
                return auto_voice_webhook.post(request)
            
            else:
                # REGULAR CALL - Use basic voice response
                response = VoiceResponse()
                
                if call_session and call_session.agent:
                    # Outbound call with assigned agent
                    agent = call_session.agent
                    receiver_name = call_session.caller_name or ""
                    
                    # Generate personalized greeting
                    if receiver_name:
                        greeting = f"Hello {receiver_name}! This is {agent.name}. How are you doing today?"
                    else:
                        greeting = f"Hello! This is {agent.name}. How are you doing today?"
                        
                else:
                    # Inbound call - assign available agent
                    agent = Agent.objects.filter(
                        agent_type__in=['inbound', 'both'],
                        status='active',
                        is_active=True
                    ).first()
                    
                    if agent:
                        # Create call session for inbound call
                        if not call_session:
                            call_session = CallSession.objects.create(
                                caller_number=from_number,
                                call_type='inbound',
                                status='active',
                                agent=agent,
                                twilio_call_sid=call_sid,
                                started_at=timezone.now()
                            )
                        
                        greeting = f"Hello! This is {agent.name}. Thank you for calling. How can I help you today?"
                        
                        # Update agent status
                        agent.status = 'on_call'
                        agent.save()
                    else:
                        # No agent available
                        greeting = "Thank you for calling. All our agents are currently busy. Please call back later."
                        response.say(greeting, voice='alice')
                        response.hangup()
                        return Response(str(response), content_type='application/xml')
                
                # Add greeting
                response.say(greeting, voice='alice', language='en-US')
                
                # Add speech gathering for conversation
                gather = response.gather(
                    input='speech',
                    timeout=10,
                    action=f'/api/calls/twilio-webhook/',  # Same endpoint handles responses
                    method='POST',
                    speech_timeout='auto'
                )
                gather.say("Please tell me how I can help you today.", voice='alice')
                
                # If no response
                response.say("I didn't hear anything. Please let me know how I can assist you.")
                response.redirect('/api/calls/twilio-webhook/')
                
                print(f"✅ Generated basic TwiML response for {call_sid}")
                return Response(str(response), content_type='application/xml')
                
        except Exception as e:
            print(f"❌ Error in active call handling: {str(e)}")
            # Fallback response
            response = VoiceResponse()
            response.say("I'm sorry, we're experiencing technical difficulties. Please try calling again.", voice='alice')
            response.hangup()
            return Response(str(response), content_type='application/xml')
    
    def _handle_status_update(self, request, call_sid, call_status):
        """Handle call status updates"""
        try:
            call_session = CallSession.objects.get(twilio_call_sid=call_sid)
            
            # Update call status based on Twilio status
            if call_status == 'answered':
                call_session.status = 'answered'
                call_session.answered_at = timezone.now()
            elif call_status == 'completed':
                call_session.status = 'completed'
                call_session.ended_at = timezone.now()
                
                # Update agent status back to available
                if call_session.agent:
                    call_session.agent.status = 'available'
                    call_session.agent.save()
            elif call_status in ['busy', 'no-answer', 'failed']:
                call_session.status = 'failed'
                call_session.ended_at = timezone.now()
                
                # Update agent status back to available
                if call_session.agent:
                    call_session.agent.status = 'available'
                    call_session.agent.save()
            
            call_session.save()
            print(f"✅ Updated call {call_sid} status to {call_status}")
            
        except CallSession.DoesNotExist:
            print(f"⚠️ Call session not found for SID: {call_sid}")
            pass
        
        # Return simple response for status updates
        response = VoiceResponse()
        return Response(str(response), content_type='application/xml')


class HomeAIIntegrationAPIView(APIView):
    """HomeAI integration for call assistance"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'call_id': openapi.Schema(type=openapi.TYPE_STRING, description='Call session ID'),
                'message': openapi.Schema(type=openapi.TYPE_STRING, description='Message to process'),
                'context': openapi.Schema(type=openapi.TYPE_STRING, description='Call context')
            },
            required=['call_id', 'message']
        ),
        responses={
            200: "AI assistance response",
            400: "Bad request",
            401: "Unauthorized"
        },
        operation_description="Get AI assistance during a call",
        tags=['Calls'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        call_id = request.data.get('call_id')
        message = request.data.get('message')
        context = request.data.get('context', '')
        
        if not call_id or not message:
            return Response({
                'error': 'Call ID and message are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            call_session = CallSession.objects.get(id=call_id)
            
            # Check if user has access to this call
            if (request.user != call_session.user and 
                request.user != call_session.agent.user and 
                request.user.role != 'admin'):
                return Response({
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Mock AI response (integrate with actual HomeAI API)
            ai_response = {
                'suggestion': f"Based on the context '{context}' and message '{message}', I suggest responding with empathy and offering specific solutions.",
                'confidence': 0.85,
                'recommended_actions': [
                    'Acknowledge customer concern',
                    'Offer specific solution',
                    'Follow up with timeline'
                ],
                'sentiment': 'neutral',
                'urgency': 'medium'
            }
            
            # Update call session with AI data
            call_session.ai_suggestions = json.dumps(ai_response)
            call_session.save()
            
            return Response({
                'ai_response': ai_response,
                'call_id': str(call_session.id)
            }, status=status.HTTP_200_OK)
            
        except CallSession.DoesNotExist:
            return Response({
                'error': 'Call session not found'
            }, status=status.HTTP_404_NOT_FOUND)


class QuickActionsAPIView(APIView):
    """Get quick actions for calls"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: "List of quick actions",
            401: "Unauthorized"
        },
        operation_description="Get available quick actions for calls",
        tags=['Calls'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        actions = QuickAction.objects.filter(is_active=True).order_by('order')
        
        data = []
        for action in actions:
            data.append({
                'id': str(action.id),
                'name': action.name,
                'action_type': action.action_type,
                'shortcut_key': action.shortcut_key,
                'icon': action.icon,
                'description': action.description
            })
        
        return Response({'actions': data}, status=status.HTTP_200_OK)


# ====================================
# CALL DATA API - Frontend Interface  
# ====================================

@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description="Call data list",
            examples={
                "application/json": {
                    "success": True,
                    "data": [
                        {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "type": "inbound",
                            "status": "completed",
                            "caller_number": "+1234567890",
                            "caller_name": "John Doe",
                            "start_time": "2025-10-13T14:30:00Z",
                            "end_time": "2025-10-13T14:35:00Z", 
                            "duration": 300,
                            "transcript": [
                                {
                                    "session_id": "session_123",
                                    "speaker": "agent",
                                    "message": "Hello, how can I help you?",
                                    "timestamp": "2025-10-13T14:30:05Z"
                                }
                            ],
                            "emotions": [
                                {
                                    "timestamp": 10.5,
                                    "emotion": "joy",
                                    "confidence": 0.85
                                }
                            ],
                            "outcome": "converted",
                            "summary": "Customer inquiry about product features",
                            "agent_id": 1,
                            "agent_name": "Sarah Agent",
                            "scheduled_time": None
                        }
                    ],
                    "count": 1
                }
            }
        )
    },
    operation_description="Get call data for both inbound and outbound calls",
    tags=['Call Data']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def call_data_list(request):
    """
    API endpoint that returns call data in the format:
    interface CallData {
      id: string;
      type: 'inbound' | 'outbound';
      status: 'active' | 'completed' | 'failed' | 'pending';
      caller_number: string;
      caller_name?: string;
      start_time: string;
      end_time?: string;
      duration?: number;
      transcript: TranscriptItem[];
      emotions: Array<{timestamp: number; emotion: string; confidence: number;}>;
      outcome?: 'answered' | 'voicemail' | 'busy' | 'no_answer' | 'converted' | 'not_interested';
      summary?: string;
      agent_id: number;
      agent_name?: string;
      scheduled_time?: string;
    }
    
    Supports both inbound and outbound calls for all users.
    """
    try:
        user = request.user
        
        # Get query parameters for filtering
        call_type = request.GET.get('type')  # 'inbound' or 'outbound'
        call_status = request.GET.get('status')  # 'active', 'completed', 'failed', 'pending' 
        agent_id = request.GET.get('agent_id')
        limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100 calls
        
        # Base queryset - filter by user access level
        if user.role == 'admin':
            # Admin can see all calls
            calls = CallSession.objects.all()
        elif user.role == 'agent':
            # Agent can see their own calls
            try:
                agent = user.agents.first()  # Get user's agent profile
                if agent:
                    calls = CallSession.objects.filter(agent=agent)
                else:
                    calls = CallSession.objects.none()
            except:
                calls = CallSession.objects.none()
        else:
            # Regular user can see their own calls
            calls = CallSession.objects.filter(user=user)
        
        # Apply filters
        if call_type in ['inbound', 'outbound']:
            calls = calls.filter(call_type=call_type)
            
        if agent_id:
            calls = calls.filter(agent_id=agent_id)
        
        # Status filtering (convert frontend status to Django status)
        if call_status:
            if call_status == 'active':
                calls = calls.filter(status='answered', ended_at__isnull=True)
            elif call_status == 'completed':
                calls = calls.filter(status='completed')
            elif call_status == 'failed':
                calls = calls.filter(status__in=['failed', 'busy', 'no_answer', 'cancelled'])
            elif call_status == 'pending':
                calls = calls.filter(status__in=['initiated', 'ringing'])
        
        # Order by most recent and limit
        calls = calls.select_related('agent').prefetch_related(
            'transcripts', 'emotions'
        ).order_by('-started_at')[:limit]
        
        # Serialize the data
        from .serializers import CallDataSerializer
        serializer = CallDataSerializer(calls, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': len(serializer.data),
            'filters': {
                'type': call_type,
                'status': call_status,
                'agent_id': agent_id,
                'limit': limit
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to fetch call data: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    responses={200: "Call detail with full transcript and emotions"},
    operation_description="Get detailed information for a specific call",
    tags=['Call Data']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def call_detail(request, call_id):
    """Get detailed information for a specific call"""
    try:
        user = request.user
        
        # Get the call with access control
        if user.role == 'admin':
            call = CallSession.objects.get(pk=call_id)
        elif user.role == 'agent':
            agent = user.agents.first()
            if agent:
                call = CallSession.objects.get(pk=call_id, agent=agent)
            else:
                return Response({
                    'success': False,
                    'error': 'Agent profile not found'
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            call = CallSession.objects.get(pk=call_id, user=user)
        
        # Serialize the call data
        from .serializers import CallDataSerializer
        serializer = CallDataSerializer(call)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except CallSession.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Call not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to fetch call detail: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'call_id': openapi.Schema(type=openapi.TYPE_STRING, description='Call ID'),
            'update_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of update'),
            'data': openapi.Schema(type=openapi.TYPE_OBJECT, description='Update data')
        }
    ),
    responses={200: "Real-time update broadcasted"},
    operation_description="Broadcast real-time updates for active calls",
    tags=['Call Data - Real-time']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def broadcast_live_update(request):
    """
    Endpoint to broadcast real-time updates during active calls
    Used for live transcript, emotions, status changes etc.
    """
    try:
        call_id = request.data.get('call_id')
        update_type = request.data.get('update_type')
        data = request.data.get('data', {})
        
        if not call_id or not update_type:
            return Response({
                'success': False,
                'error': 'call_id and update_type are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify call exists and user has access
        try:
            call = CallSession.objects.get(pk=call_id)
            
            # Check access permissions
            user = request.user
            if user.role != 'admin':
                if user.role == 'agent':
                    agent = user.agents.first()
                    if not agent or call.agent != agent:
                        return Response({
                            'success': False,
                            'error': 'Access denied'
                        }, status=status.HTTP_403_FORBIDDEN)
                elif call.user != user:
                    return Response({
                        'success': False,
                        'error': 'Access denied'
                    }, status=status.HTTP_403_FORBIDDEN)
        except CallSession.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Call not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Add timestamp if not provided
        if 'timestamp' not in data:
            from django.utils import timezone
            data['timestamp'] = timezone.now().isoformat()
        
        # Broadcast the update
        from .signals import broadcast_live_call_update
        broadcast_live_call_update(call_id, update_type, data)
        
        return Response({
            'success': True,
            'message': 'Update broadcasted successfully',
            'call_id': call_id,
            'update_type': update_type
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to broadcast update: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    responses={200: "WebSocket connection info"},
    operation_description="Get WebSocket connection information and instructions",
    tags=['Call Data - Real-time']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def websocket_info(request):
    """
    Provide WebSocket connection information for real-time updates
    """
    try:
        user = request.user
        
        # Get WebSocket URL (you might want to make this configurable)
        ws_base_url = request.build_absolute_uri('/').replace('http', 'ws').replace('https', 'wss')
        ws_url = f"{ws_base_url}ws/calls/full/"
        
        return Response({
            'success': True,
            'websocket': {
                'url': ws_url,
                'connection_info': {
                    'user_id': user.id,
                    'user_role': user.role,
                    'groups': {
                        'user_specific': f'user_{user.id}',
                        'role_based': f'{user.role}_calls' if user.role in ['admin', 'agent'] else None,
                        'general': 'calls_updates'
                    }
                },
                'authentication': {
                    'method': 'JWT Token in query parameter',
                    'parameter': 'token',
                    'example': f'{ws_url}?token=YOUR_JWT_TOKEN'
                },
                'message_types': {
                    'outgoing': {
                        'ping': 'Keep connection alive',
                        'subscribe_to_call': 'Subscribe to specific call updates',
                        'unsubscribe_from_call': 'Unsubscribe from call updates'
                    },
                    'incoming': {
                        'call_created': 'New call initiated',
                        'call_status_update': 'Call status changed',
                        'call_ended': 'Call ended',
                        'transcript_update': 'Real-time transcript',
                        'emotion_update': 'Real-time emotion analysis',
                        'call_data_update': 'Complete call data update',
                        'live_call_update': 'Live updates during call'
                    }
                }
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to get WebSocket info: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([])  # No auth for Twilio webhooks
def fallback_handler(request):
    """
    Fallback handler when main webhook fails
    Agar main webhook fail ho jaye toh yeh backup response dega
    """
    try:
        # Log the fallback trigger
        call_sid = request.data.get('CallSid', 'Unknown')
        from_number = request.data.get('From', 'Unknown')
        
        # Simple fallback response
        response = VoiceResponse()
        response.say(
            "I'm sorry, we're experiencing technical difficulties. Please try calling again in a few minutes.",
            voice='alice',
            language='en-US'
        )
        
        # Optional: Add a simple gather for basic interaction
        gather = response.gather(
            input='speech',
            timeout=5,
            speech_timeout='auto'
        )
        gather.say("If this is urgent, please say 'urgent' now.")
        
        # If still no response, end gracefully
        response.say("Thank you for calling. We'll be back online shortly.")
        response.hangup()
        
        return Response(str(response), content_type='application/xml')
        
    except Exception as e:
        # Emergency fallback
        response = VoiceResponse()
        response.say("We apologize for the inconvenience. Please try again later.")
        response.hangup()
        return Response(str(response), content_type='application/xml')


@api_view(['POST'])
@permission_classes([])  # No auth for Twilio webhooks  
def status_callback(request):
    """
    Handle call status changes from Twilio
    Twilio se call status updates receive karta hai
    """
    try:
        # Get call information from Twilio
        call_sid = request.data.get('CallSid')
        call_status = request.data.get('CallStatus')  # initiated, ringing, answered, completed, etc.
        from_number = request.data.get('From')
        to_number = request.data.get('To')
        direction = request.data.get('Direction')  # inbound or outbound
        duration = request.data.get('CallDuration')
        
        # Log the status change
        print(f"📞 Call Status Update: {call_sid} - {call_status}")
        
        # Update database if call exists
        try:
            call_session = CallSession.objects.get(twilio_call_sid=call_sid)
            
            # Update status
            old_status = call_session.status
            call_session.status = call_status
            
            # Update timestamps based on status
            if call_status == 'answered' and not call_session.answered_at:
                call_session.answered_at = timezone.now()
            elif call_status == 'completed' and not call_session.ended_at:
                call_session.ended_at = timezone.now()
                if duration:
                    call_session.duration = int(duration)
            elif call_status in ['failed', 'busy', 'no-answer', 'cancelled']:
                call_session.ended_at = timezone.now()
                call_session.status = 'failed'
            
            call_session.save()
            
            # Broadcast real-time update if status changed
            if old_status != call_status:
                from .broadcasting import CallBroadcasting
                broadcaster = CallBroadcasting()
                broadcaster.broadcast_call_status_update(
                    call_session=call_session,
                    user_id=call_session.user_id,
                    agent_id=call_session.agent_id if call_session.agent else None
                )
            
            print(f"✅ Updated call {call_sid}: {old_status} → {call_status}")
            
        except CallSession.DoesNotExist:
            print(f"⚠️ Call session not found for SID: {call_sid}")
            # Could be a call initiated outside our system
            pass
        
        # Always return success to Twilio
        return Response({
            'status': 'received',
            'call_sid': call_sid,
            'call_status': call_status,
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Status callback error: {str(e)}")
        # Still return success to avoid Twilio retries
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_200_OK)


# Voice Response Handler for Twilio (REQUIRED for agent response)
@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])  # Twilio webhook
def voice_response_handler(request):
    """
    Voice response handler for Twilio calls
    This endpoint is called when call is answered
    """
    from django.http import HttpResponse
    
    print(f"🎤 Voice Response Handler Called")
    print(f"   Method: {request.method}")
    print(f"   Data: {request.POST if request.method == 'POST' else request.GET}")
    
    try:
        # Create TwiML response
        response = VoiceResponse()
        
        # Get call SID from request
        call_sid = request.POST.get('CallSid') or request.GET.get('CallSid')
        from_number = request.POST.get('From') or request.GET.get('From')
        to_number = request.POST.get('To') or request.GET.get('To')
        
        print(f"   Call SID: {call_sid}")
        print(f"   From: {from_number} To: {to_number}")
        
        # Find the call session
        if call_sid:
            try:
                call_session = CallSession.objects.get(twilio_call_sid=call_sid)
                
                # Get agent configuration
                if call_session.agent:
                    agent = call_session.agent
                    
                    # Simple greeting for now
                    greeting = f"Hello! This is {agent.name}. How can I help you today?"
                    
                    # Add voice response
                    response.say(greeting, voice='alice', language='en-US')
                    
                    # Add a pause and then gather input
                    response.pause(length=1)
                    
                    # Gather customer response
                    gather = response.gather(
                        input='speech',
                        timeout=10,
                        speech_timeout='auto',
                        action=f"{settings.BASE_URL}api/calls/voice-response/",
                        method='POST'
                    )
                    
                    gather.say("Please tell me how I can assist you.", voice='alice')
                    
                    # Fallback if no input
                    response.say("I didn't hear anything. Please call back if you need assistance.", voice='alice')
                    response.hangup()
                    
                    print(f"✅ Generated TwiML response for agent: {agent.name}")
                    
                else:
                    # No agent assigned - basic response
                    response.say("Hello! Thank you for calling. Please hold while we connect you.", voice='alice')
                    response.pause(length=2)
                    response.hangup()
                    
                    print(f"⚠️ No agent assigned to call")
                
            except CallSession.DoesNotExist:
                print(f"❌ Call session not found for SID: {call_sid}")
                response.say("Thank you for calling. We are experiencing technical difficulties.", voice='alice')
                response.hangup()
        
        else:
            # No call SID - basic response
            print(f"❌ No Call SID provided")
            response.say("Hello! Thank you for calling.", voice='alice')
            response.hangup()
        
        # Return TwiML response
        twiml_str = str(response)
        print(f"📞 TwiML Response: {twiml_str}")
        
        return HttpResponse(twiml_str, content_type='text/xml')
        
    except Exception as e:
        print(f"❌ Voice response error: {str(e)}")
        
        # Emergency fallback TwiML
        emergency_response = VoiceResponse()
        emergency_response.say("Thank you for calling. Please try again later.", voice='alice')
        emergency_response.hangup()
        
        return HttpResponse(str(emergency_response), content_type='text/xml')


# Call Status Handler for Twilio
@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Twilio webhook
def call_status_handler(request):
    """
    Call status updates from Twilio
    """
    print(f"📊 Call Status Handler Called")
    print(f"   Data: {request.POST}")
    
    try:
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        call_duration = request.POST.get('CallDuration')
        
        print(f"   Call SID: {call_sid}")
        print(f"   Status: {call_status}")
        print(f"   Duration: {call_duration}")
        
        if call_sid:
            try:
                call_session = CallSession.objects.get(twilio_call_sid=call_sid)
                
                # Update call status
                call_session.status = call_status.lower()
                
                if call_status in ['completed', 'busy', 'no-answer', 'failed', 'canceled']:
                    call_session.ended_at = timezone.now()
                
                call_session.save()
                
                print(f"✅ Updated call session: {call_session.id}")
                
                # Broadcast update
                from .broadcasting import broadcast_call_status_update
                broadcast_call_status_update(call_session)
                
            except CallSession.DoesNotExist:
                print(f"❌ Call session not found for SID: {call_sid}")
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Call status error: {str(e)}")
        return Response({'status': 'error'}, status=status.HTTP_200_OK)


# REAL-TIME WEBHOOK TESTING - Local Development
@api_view(['POST', 'GET'])
@permission_classes([permissions.AllowAny])  # Allow Twilio and testing tools
def test_webhook_handler(request):
    """
    Real-time webhook testing handler for local development
    Real-time mein webhook response check karne ke liye
    """
    from django.http import HttpResponse
    from datetime import datetime
    import json
    
    try:
        print(f"\n🔔 TEST WEBHOOK RECEIVED: {datetime.now()}")
        print("=" * 60)
        
        # Log all incoming data
        print(f"📋 Method: {request.method}")
        
        if request.method == 'POST':
            # Handle both form data and raw body
            try:
                if hasattr(request, 'POST') and request.POST:
                    print(f"� POST Data: {dict(request.POST)}")
                    call_sid = request.POST.get('CallSid', 'TEST_CALL_' + str(int(time.time())))
                    call_status = request.POST.get('CallStatus', 'in-progress')
                    from_number = request.POST.get('From', '+923110571480')
                    to_number = request.POST.get('To', '+12182315749')
                else:
                    # Fallback for raw body
                    print(f"📦 Raw Body: {request.body}")
                    call_sid = 'TEST_CALL_' + str(int(time.time()))
                    call_status = 'in-progress'
                    from_number = '+923110571480'
                    to_number = '+12182315749'
            except Exception as parse_error:
                print(f"⚠️  Data parse warning: {parse_error}")
                call_sid = 'TEST_CALL_' + str(int(time.time()))
                call_status = 'in-progress'
                from_number = '+923110571480'
                to_number = '+12182315749'
                
        else:  # GET request for testing
            call_sid = 'TEST_GET_CALL'
            call_status = 'in-progress'
            from_number = '+923110571480'
            to_number = '+12182315749'
        
        print(f"🎯 CALL DETAILS:")
        print(f"  📞 CallSid: {call_sid}")
        print(f"  📊 Status: {call_status}")
        print(f"  📱 From: {from_number}")
        print(f"  📞 To: {to_number}")
        
        # Create TwiML response with real-time testing
        response = VoiceResponse()
        
        # Dynamic voice response with current time
        current_time = datetime.now().strftime('%H:%M:%S')
        
        if call_status == 'in-progress':
            # Active call - agent speaks
            greeting = f"""
            Hello! This is your AI Voice Agent speaking from the webhook test handler.
            Current time is {current_time}.
            Call ID ending in {call_sid[-6:] if len(call_sid) > 6 else call_sid}.
            Can you hear me clearly? This is a real-time webhook test.
            """
            
            response.say(greeting.strip(), voice='alice', language='en-US')
            response.pause(length=2)
            
            # Gather customer response
            gather = response.gather(
                input='speech',
                timeout=10,
                action='/api/calls/test-webhook/',
                method='POST',
                speech_timeout='auto'
            )
            gather.say("Please respond with yes or no to confirm you can hear me.", voice='alice')
            
            # If no response
            response.say("Thank you for testing the webhook. The connection is working perfectly!", voice='alice')
            
        else:
            # Call status update or ending
            response.say(f"Webhook test completed at {current_time}. Thank you!", voice='alice')
        
        # Generate TwiML XML
        twiml_xml = str(response)
        
        print(f"🎤 TWIML RESPONSE GENERATED:")
        print("-" * 40)
        print(twiml_xml)
        print("-" * 40)
        
        # Log response details
        print(f"✅ Response sent successfully")
        print(f"📊 Content-Type: application/xml")
        print(f"📝 Length: {len(twiml_xml)} characters")
        print("=" * 60)
        
        return HttpResponse(twiml_xml, content_type='application/xml')
        
    except Exception as e:
        print(f"❌ Webhook handler error: {str(e)}")
        # Return simple TwiML even on error
        response = VoiceResponse()
        response.say("Hello, this is a test webhook response.", voice='alice')
        return HttpResponse(str(response), content_type='application/xml')


# WEBHOOK STATUS CHECKER - Real-time monitoring
@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def webhook_status_checker(request):
    """
    Webhook status checker for real-time monitoring
    Webhook ki status real-time mein check karne ke liye
    """
    from django.http import JsonResponse
    
    status_data = {
        'timestamp': timezone.now().isoformat(),
        'webhook_status': 'active',
        'server_status': 'running',
        'method': request.method,
        'remote_addr': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
        'content_type': request.META.get('CONTENT_TYPE'),
        'twilio_test': {
            'expected_content_type': 'application/x-www-form-urlencoded',
            'expected_fields': ['CallSid', 'CallStatus', 'From', 'To'],
            'webhook_url': request.build_absolute_uri('/api/calls/test-webhook/'),
            'status_url': request.build_absolute_uri('/api/calls/webhook-status/')
        },
        'environment': {
            'debug': getattr(settings, 'DEBUG', False),
            'base_url': getattr(settings, 'BASE_URL', 'Not configured')
        }
    }
    
    if request.method == 'POST':
        status_data['post_data'] = dict(request.POST)
        status_data['has_call_sid'] = 'CallSid' in request.POST
        status_data['has_call_status'] = 'CallStatus' in request.POST
    
    print(f"🔍 WEBHOOK STATUS CHECK: {status_data['timestamp']}")
    print(f"📊 Method: {request.method}")
    print(f"🌐 Remote: {status_data['remote_addr']}")
    
    return JsonResponse(status_data, status=200)
