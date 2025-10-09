from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db import models
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json
from datetime import datetime, timedelta

from .ai_agent_models import (
    AIAgent, CustomerProfile, CallSession, 
    AIAgentTraining, ScheduledCallback
)
from .homeai_integration import HomeAIService, MockHomeAIService
from .twilio_service import TwilioCallService

User = get_user_model()


class AIAgentListCreateAPIView(generics.ListCreateAPIView):
    """
    Complete CRUD - List all AI Agents or Create new one
    Admin can see all agents, Client can see only their agent
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return AIAgent.objects.all().order_by('-created_at')
        else:
            return AIAgent.objects.filter(client=user)
    
    @swagger_auto_schema(
        responses={
            200: "List of AI Agents",
            401: "Unauthorized"
        },
        operation_description="Get list of AI Agents - Admin sees all, Client sees only their agent",
        tags=['AI Agents']
    )
    def get(self, request, *args, **kwargs):
        agents = self.get_queryset()
        
        agents_data = []
        for agent in agents:
            agents_data.append({
                'id': str(agent.id),
                'name': agent.name,
                'client_email': agent.client.email,
                'client_name': agent.client.get_full_name(),
                'status': agent.status,
                'personality_type': agent.personality_type,
                'training_level': agent.training_level,
                'calls_handled': agent.calls_handled,
                'conversion_rate': agent.conversion_rate,
                'is_ready_for_calls': agent.is_ready_for_calls,
                'created_at': agent.created_at.isoformat(),
                'updated_at': agent.updated_at.isoformat(),
                'working_hours': {
                    'start': agent.working_hours_start.strftime('%H:%M'),
                    'end': agent.working_hours_end.strftime('%H:%M')
                },
                'performance': {
                    'successful_conversions': agent.successful_conversions,
                    'customer_satisfaction': agent.customer_satisfaction,
                    'avg_call_duration': agent.avg_call_duration
                }
            })
        
        return Response({
            'agents': agents_data,
            'total_count': len(agents_data),
            'user_role': request.user.role
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Agent name'),
                'personality_type': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    enum=['friendly', 'professional', 'persuasive', 'supportive', 'custom'],
                    description='Agent personality'
                ),
                'voice_model': openapi.Schema(type=openapi.TYPE_STRING, description='Voice model'),
                'working_hours_start': openapi.Schema(type=openapi.TYPE_STRING, description='09:00 format'),
                'working_hours_end': openapi.Schema(type=openapi.TYPE_STRING, description='18:00 format'),
                'max_daily_calls': openapi.Schema(type=openapi.TYPE_INTEGER, description='Max calls per day'),
                'business_info': openapi.Schema(type=openapi.TYPE_OBJECT, description='Business information'),
                'sales_goals': openapi.Schema(type=openapi.TYPE_OBJECT, description='Sales targets'),
                'initial_script': openapi.Schema(type=openapi.TYPE_STRING, description='Initial sales script')
            },
            required=['name']
        ),
        responses={
            201: "AI Agent created successfully",
            400: "Bad request",
            409: "Agent already exists"
        },
        operation_description="Create new AI Agent for client",
        tags=['AI Agents']
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        
        # Check if agent already exists for this client
        if AIAgent.objects.filter(client=user).exists():
            existing_agent = AIAgent.objects.get(client=user)
            return Response({
                'error': 'AI Agent already exists for this client',
                'existing_agent': {
                    'id': str(existing_agent.id),
                    'name': existing_agent.name,
                    'status': existing_agent.status,
                    'created_at': existing_agent.created_at.isoformat()
                },
                'message': 'Use PUT/PATCH to update existing agent or DELETE to remove it'
            }, status=status.HTTP_409_CONFLICT)
        
        data = request.data
        
        try:
            with transaction.atomic():
                # Create AI Agent
                agent = AIAgent.objects.create(
                    client=user,
                    name=data.get('name'),
                    personality_type=data.get('personality_type', 'friendly'),
                    voice_model=data.get('voice_model', 'en-US-female-1'),
                    status='training',
                    training_level=0,
                    working_hours_start=data.get('working_hours_start', '09:00'),
                    working_hours_end=data.get('working_hours_end', '18:00'),
                    max_daily_calls=data.get('max_daily_calls', 50),
                    conversation_memory={
                        'business_info': data.get('business_info', {}),
                        'created_at': datetime.now().isoformat(),
                        'initial_setup': True,
                        'created_by': user.email
                    }
                )
                
                # Create initial training session if script provided
                if data.get('initial_script'):
                    AIAgentTraining.objects.create(
                        ai_agent=agent,
                        training_type='initial',
                        training_data={
                            'initial_script': data.get('initial_script'),
                            'business_info': data.get('business_info', {}),
                            'setup_timestamp': datetime.now().isoformat()
                        },
                        client_instructions=data.get('initial_script', ''),
                        sales_goals=data.get('sales_goals', {}),
                        product_info=data.get('business_info', {}),
                        completion_percentage=0
                    )
                
                return Response({
                    'message': 'AI Agent created successfully',
                    'agent': {
                        'id': str(agent.id),
                        'name': agent.name,
                        'status': agent.status,
                        'training_level': agent.training_level,
                        'personality_type': agent.personality_type,
                        'is_ready_for_calls': agent.is_ready_for_calls,
                        'created_at': agent.created_at.isoformat()
                    },
                    'next_steps': [
                        'Complete agent training via /api/agents/ai/training/',
                        'Configure business information and sales scripts',
                        'Start making calls when training_level >= 20%'
                    ]
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({
                'error': f'Failed to create AI Agent: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class AIAgentDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Complete CRUD - Read, Update, Delete specific AI Agent
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get_object(self):
        agent_id = self.kwargs.get('id')
        user = self.request.user
        
        if user.role == 'admin':
            return get_object_or_404(AIAgent, id=agent_id)
        else:
            return get_object_or_404(AIAgent, id=agent_id, client=user)
    
    @swagger_auto_schema(
        responses={
            200: "AI Agent details",
            404: "Agent not found"
        },
        operation_description="Get detailed information about specific AI Agent",
        tags=['AI Agents']
    )
    def get(self, request, *args, **kwargs):
        agent = self.get_object()
        
        # Get related data
        recent_calls = CallSession.objects.filter(ai_agent=agent).order_by('-initiated_at')[:5]
        total_customers = CustomerProfile.objects.filter(ai_agent=agent).count()
        pending_callbacks = ScheduledCallback.objects.filter(
            ai_agent=agent, 
            status='scheduled'
        ).count()
        training_sessions = AIAgentTraining.objects.filter(ai_agent=agent).count()
        
        # Recent calls data
        calls_data = []
        for call in recent_calls:
            calls_data.append({
                'id': str(call.id),
                'phone_number': call.phone_number,
                'call_type': call.call_type,
                'outcome': call.outcome,
                'duration': call.duration_formatted,
                'initiated_at': call.initiated_at.isoformat()
            })
        
        agent_data = {
            'id': str(agent.id),
            'name': agent.name,
            'client': {
                'id': str(agent.client.id),
                'email': agent.client.email,
                'full_name': agent.client.get_full_name()
            },
            'status': agent.status,
            'personality_type': agent.personality_type,
            'voice_model': agent.voice_model,
            'training_level': agent.training_level,
            'is_ready_for_calls': agent.is_ready_for_calls,
            'working_hours': {
                'start': agent.working_hours_start.strftime('%H:%M'),
                'end': agent.working_hours_end.strftime('%H:%M')
            },
            'max_daily_calls': agent.max_daily_calls,
            'performance_metrics': {
                'calls_handled': agent.calls_handled,
                'successful_conversions': agent.successful_conversions,
                'conversion_rate': agent.conversion_rate,
                'avg_call_duration': agent.avg_call_duration,
                'customer_satisfaction': agent.customer_satisfaction
            },
            'statistics': {
                'total_customers': total_customers,
                'pending_callbacks': pending_callbacks,
                'training_sessions': training_sessions,
                'recent_calls': calls_data
            },
            'conversation_memory': agent.conversation_memory,
            'customer_preferences': agent.customer_preferences,
            'created_at': agent.created_at.isoformat(),
            'updated_at': agent.updated_at.isoformat()
        }
        
        return Response(agent_data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Agent name'),
                'personality_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['friendly', 'professional', 'persuasive', 'supportive', 'custom']
                ),
                'voice_model': openapi.Schema(type=openapi.TYPE_STRING),
                'working_hours_start': openapi.Schema(type=openapi.TYPE_STRING),
                'working_hours_end': openapi.Schema(type=openapi.TYPE_STRING),
                'max_daily_calls': openapi.Schema(type=openapi.TYPE_INTEGER),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['training', 'learning', 'active', 'optimizing', 'paused']
                ),
                'business_info': openapi.Schema(type=openapi.TYPE_OBJECT),
                'sales_script': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            200: "Agent updated successfully",
            404: "Agent not found"
        },
        operation_description="Update AI Agent details",
        tags=['AI Agents']
    )
    def put(self, request, *args, **kwargs):
        agent = self.get_object()
        data = request.data
        
        # Update basic fields
        if 'name' in data:
            agent.name = data['name']
        if 'personality_type' in data:
            agent.personality_type = data['personality_type']
        if 'voice_model' in data:
            agent.voice_model = data['voice_model']
        if 'working_hours_start' in data:
            agent.working_hours_start = data['working_hours_start']
        if 'working_hours_end' in data:
            agent.working_hours_end = data['working_hours_end']
        if 'max_daily_calls' in data:
            agent.max_daily_calls = data['max_daily_calls']
        if 'status' in data and request.user.role in ['admin', 'agent']:
            agent.status = data['status']
        
        # Update conversation memory
        if 'business_info' in data:
            if 'business_info' not in agent.conversation_memory:
                agent.conversation_memory['business_info'] = {}
            agent.conversation_memory['business_info'].update(data['business_info'])
            agent.conversation_memory['last_updated'] = datetime.now().isoformat()
        
        # Update sales script
        if 'sales_script' in data:
            agent.sales_script = data['sales_script']
            agent.conversation_memory['sales_script_updated'] = datetime.now().isoformat()
        
        agent.save()
        
        return Response({
            'message': 'AI Agent updated successfully',
            'agent': {
                'id': str(agent.id),
                'name': agent.name,
                'status': agent.status,
                'personality_type': agent.personality_type,
                'training_level': agent.training_level,
                'updated_at': agent.updated_at.isoformat()
            }
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'personality_type': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            200: "Agent partially updated",
            404: "Agent not found"
        },
        operation_description="Partially update AI Agent",
        tags=['AI Agents']
    )
    def patch(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        responses={
            204: "Agent deleted successfully",
            404: "Agent not found",
            400: "Cannot delete agent with active calls"
        },
        operation_description="Delete AI Agent and all related data",
        tags=['AI Agents']
    )
    def delete(self, request, *args, **kwargs):
        agent = self.get_object()
        
        # Check for active calls
        active_calls = CallSession.objects.filter(
            ai_agent=agent,
            outcome__in=['answered', 'in_progress']
        ).count()
        
        if active_calls > 0:
            return Response({
                'error': 'Cannot delete agent with active calls',
                'active_calls_count': active_calls,
                'message': 'Please wait for active calls to complete or manually end them'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            agent_name = agent.name
            client_email = agent.client.email
            
            # Delete all related data
            with transaction.atomic():
                # Delete in proper order to avoid foreign key issues
                ScheduledCallback.objects.filter(ai_agent=agent).delete()
                CallSession.objects.filter(ai_agent=agent).delete()
                CustomerProfile.objects.filter(ai_agent=agent).delete()
                AIAgentTraining.objects.filter(ai_agent=agent).delete()
                
                # Finally delete the agent
                agent.delete()
            
            return Response({
                'message': f'AI Agent "{agent_name}" deleted successfully',
                'deleted_agent': {
                    'name': agent_name,
                    'client_email': client_email,
                    'deleted_at': datetime.now().isoformat()
                },
                'note': 'All related data (calls, customers, training) has been permanently deleted'
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response({
                'error': f'Failed to delete agent: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class AIAgentBulkActionsAPIView(APIView):
    """Bulk operations on AI Agents - Admin only"""
    permission_classes = [permissions.IsAuthenticated]
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({
                'error': 'Admin access required for bulk operations'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().dispatch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'action': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['activate', 'pause', 'reset_training', 'delete_inactive'],
                    description='Bulk action to perform'
                ),
                'agent_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description='List of agent IDs'
                ),
                'filters': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description='Filters for bulk action (alternative to agent_ids)'
                )
            },
            required=['action']
        ),
        responses={200: "Bulk action completed"},
        operation_description="Perform bulk actions on AI Agents - Admin only",
        tags=['AI Agents']
    )
    def post(self, request):
        data = request.data
        action = data.get('action')
        agent_ids = data.get('agent_ids', [])
        filters = data.get('filters', {})
        
        # Get agents based on IDs or filters
        if agent_ids:
            agents = AIAgent.objects.filter(id__in=agent_ids)
        else:
            agents = AIAgent.objects.all()
            if filters.get('status'):
                agents = agents.filter(status=filters['status'])
            if filters.get('training_level_lt'):
                agents = agents.filter(training_level__lt=filters['training_level_lt'])
            if filters.get('inactive_days'):
                cutoff_date = timezone.now() - timedelta(days=filters['inactive_days'])
                agents = agents.filter(updated_at__lt=cutoff_date)
        
        results = []
        
        try:
            with transaction.atomic():
                if action == 'activate':
                    updated = agents.update(status='active')
                    results.append(f'{updated} agents activated')
                
                elif action == 'pause':
                    updated = agents.update(status='paused')
                    results.append(f'{updated} agents paused')
                
                elif action == 'reset_training':
                    for agent in agents:
                        agent.training_level = 0
                        agent.status = 'training'
                        agent.conversation_memory = {
                            'reset_at': datetime.now().isoformat(),
                            'reset_by': request.user.email
                        }
                        agent.save()
                    results.append(f'{agents.count()} agents training reset')
                
                elif action == 'delete_inactive':
                    # Only delete agents with no recent activity
                    inactive_agents = agents.filter(
                        status='paused',
                        calls_handled=0
                    )
                    count = inactive_agents.count()
                    
                    for agent in inactive_agents:
                        # Delete related data first
                        ScheduledCallback.objects.filter(ai_agent=agent).delete()
                        CallSession.objects.filter(ai_agent=agent).delete()
                        CustomerProfile.objects.filter(ai_agent=agent).delete()
                        AIAgentTraining.objects.filter(ai_agent=agent).delete()
                    
                    inactive_agents.delete()
                    results.append(f'{count} inactive agents deleted')
        
            return Response({
                'message': 'Bulk action completed successfully',
                'action': action,
                'results': results,
                'processed_count': agents.count(),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Bulk action failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class AIAgentStatsAPIView(APIView):
    """Get comprehensive statistics for AI Agents"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('agent_id', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('time_period', openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=['today', 'week', 'month', 'all']),
        ],
        responses={200: "AI Agent statistics"},
        tags=['AI Agents']
    )
    def get(self, request):
        user = request.user
        agent_id = request.query_params.get('agent_id')
        time_period = request.query_params.get('time_period', 'all')
        
        # Get agents based on user role
        if user.role == 'admin':
            if agent_id:
                agents = AIAgent.objects.filter(id=agent_id)
            else:
                agents = AIAgent.objects.all()
        else:
            agents = AIAgent.objects.filter(client=user)
            if agent_id:
                agents = agents.filter(id=agent_id)
        
        # Time filtering
        now = timezone.now()
        if time_period == 'today':
            time_filter = now.date()
            calls = CallSession.objects.filter(initiated_at__date=time_filter)
        elif time_period == 'week':
            time_filter = now - timedelta(days=7)
            calls = CallSession.objects.filter(initiated_at__gte=time_filter)
        elif time_period == 'month':
            time_filter = now.replace(day=1)
            calls = CallSession.objects.filter(initiated_at__gte=time_filter)
        else:
            calls = CallSession.objects.all()
        
        # Filter calls by agents
        calls = calls.filter(ai_agent__in=agents)
        
        # Calculate statistics
        stats = {
            'agents_overview': {
                'total_agents': agents.count(),
                'active_agents': agents.filter(status='active').count(),
                'training_agents': agents.filter(status='training').count(),
                'paused_agents': agents.filter(status='paused').count(),
                'ready_for_calls': agents.filter(training_level__gte=20).count()
            },
            'call_statistics': {
                'total_calls': calls.count(),
                'successful_calls': calls.filter(outcome__in=['interested', 'converted']).count(),
                'converted_calls': calls.filter(outcome='converted').count(),
                'callback_requests': calls.filter(outcome='callback_requested').count(),
                'avg_call_duration': calls.aggregate(avg=models.Avg('duration_seconds'))['avg'] or 0
            },
            'customer_statistics': {
                'total_customers': CustomerProfile.objects.filter(ai_agent__in=agents).count(),
                'hot_leads': CustomerProfile.objects.filter(ai_agent__in=agents, interest_level='hot').count(),
                'converted_customers': CustomerProfile.objects.filter(ai_agent__in=agents, is_converted=True).count(),
                'pending_callbacks': ScheduledCallback.objects.filter(ai_agent__in=agents, status='scheduled').count()
            },
            'performance_metrics': {
                'overall_conversion_rate': 0,
                'avg_customer_satisfaction': 0,
                'total_training_sessions': AIAgentTraining.objects.filter(ai_agent__in=agents).count()
            },
            'time_period': time_period
        }
        
        # Calculate conversion rate
        if stats['call_statistics']['total_calls'] > 0:
            stats['performance_metrics']['overall_conversion_rate'] = (
                stats['call_statistics']['converted_calls'] / stats['call_statistics']['total_calls'] * 100
            )
        
        # Calculate average satisfaction
        if agents.exists():
            stats['performance_metrics']['avg_customer_satisfaction'] = agents.aggregate(
                avg=models.Avg('customer_satisfaction')
            )['avg'] or 0
        
        return Response(stats, status=status.HTTP_200_OK)
