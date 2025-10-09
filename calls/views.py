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
                    'name': call.agent.user.get_full_name(),
                    'employee_id': call.agent.employee_id
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
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number to call'),
                'call_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of call (inbound/outbound)'),
                'priority': openapi.Schema(type=openapi.TYPE_STRING, description='Call priority (low/medium/high)')
            },
            required=['phone_number', 'call_type']
        ),
        responses={
            201: "Call started successfully",
            400: "Bad request",
            401: "Unauthorized"
        },
        operation_description="Start a new call session",
        tags=['Calls'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        call_type = request.data.get('call_type', 'outbound')
        priority = request.data.get('priority', 'medium')
        
        if not phone_number:
            return Response({
                'error': 'Phone number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create call session
        call_session = CallSession.objects.create(
            user=request.user,
            phone_number=phone_number,
            call_type=call_type,
            status='initiated'
        )
        
        # Add to queue if no agents available
        available_agent = Agent.objects.filter(
            status='available',
            is_active=True
        ).first()
        
        if not available_agent:
            # Add to queue
            CallQueue.objects.create(
                phone_number=phone_number,
                priority=priority,
                call_session=call_session
            )
            
            return Response({
                'message': 'Call added to queue',
                'call_id': str(call_session.id),
                'status': 'queued'
            }, status=status.HTTP_201_CREATED)
        
        # Assign to available agent
        call_session.agent = available_agent
        call_session.status = 'connecting'
        call_session.save()
        
        # Update agent status
        available_agent.status = 'on_call'
        available_agent.save()
        
        # Here you would integrate with Twilio to actually make the call
        # For now, we'll return a success response
        
        return Response({
            'message': 'Call initiated successfully',
            'call_id': str(call_session.id),
            'agent': {
                'id': str(available_agent.id),
                'name': available_agent.user.get_full_name(),
                'employee_id': available_agent.employee_id
            },
            'status': 'connecting'
        }, status=status.HTTP_201_CREATED)


class TwilioWebhookAPIView(APIView):
    """Handle Twilio webhooks for call events"""
    permission_classes = []  # Twilio webhooks don't need authentication
    
    def post(self, request):
        """Handle Twilio call status updates"""
        call_sid = request.data.get('CallSid')
        call_status = request.data.get('CallStatus')
        
        # Find the call session
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
            
        except CallSession.DoesNotExist:
            pass
        
        # Return TwiML response
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
