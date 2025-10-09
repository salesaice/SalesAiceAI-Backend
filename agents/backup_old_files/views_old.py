from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timedelta

from .models import Agent, AgentPerformance
from calls.models import CallSession

User = get_user_model()


class AgentProfileAPIView(APIView):
    """Manage agent profile"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: "Agent profile",
            401: "Unauthorized",
            404: "Agent profile not found"
        },
        operation_description="Get agent profile information", 
        tags=['AI Agents'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            agent = request.user.agent_profile
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get recent performance
        today = timezone.now().date()
        today_performance = AgentPerformance.objects.filter(
            agent=agent, date=today
        ).first()
        
        # Get recent calls
        recent_calls = CallSession.objects.filter(
            agent=agent
        ).order_by('-started_at')[:10]
        
        profile_data = {
            'id': str(agent.id),
            'user': {
                'id': str(agent.user.id),
                'name': agent.user.get_full_name(),
                'email': agent.user.email,
                'phone': agent.user.phone
            },
            'employee_id': agent.employee_id,
            'department': agent.department,
            'team': agent.team,
            'status': agent.status,
            'skill_level': agent.skill_level,
            'languages': agent.languages,
            'specializations': agent.specializations,
            'working_hours': agent.working_hours,
            'last_activity': agent.last_activity.isoformat(),
            'performance': {
                'total_calls': agent.total_calls,
                'successful_calls': agent.successful_calls,
                'success_rate': agent.success_rate,
                'average_call_duration': agent.average_call_duration,
                'customer_satisfaction': agent.customer_satisfaction
            },
            'today_performance': {
                'calls': today_performance.total_calls if today_performance else 0,
                'completed': today_performance.completed_calls if today_performance else 0,
                'avg_talk_time': today_performance.average_talk_time if today_performance else 0,
                'satisfaction': today_performance.customer_satisfaction if today_performance else 0
            } if today_performance else None,
            'ai_settings': {
                'use_ai_assistance': agent.use_ai_assistance,
                'ai_confidence_threshold': agent.ai_confidence_threshold,
                'preferred_ai_model': agent.preferred_ai_model
            },
            'recent_calls': [
                {
                    'id': str(call.id),
                    'type': call.call_type,
                    'status': call.status,
                    'duration': call.call_duration_formatted,
                    'phone_number': call.phone_number,
                    'started_at': call.started_at.isoformat(),
                    'customer_satisfaction': call.customer_satisfaction
                } for call in recent_calls
            ],
            'hired_date': agent.hired_date.isoformat(),
            'created_at': agent.created_at.isoformat()
        }
        
        return Response(profile_data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'languages': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                'specializations': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                'working_hours': openapi.Schema(type=openapi.TYPE_OBJECT),
                'use_ai_assistance': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'ai_confidence_threshold': openapi.Schema(type=openapi.TYPE_NUMBER),
                'preferred_ai_model': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            200: "Profile updated successfully",
            400: "Bad request",
            401: "Unauthorized",
            404: "Agent profile not found"
        },
        operation_description="Update agent profile",
        tags=['AI Agents'],
        security=[{'Bearer': []}]
    )
    def patch(self, request):
        try:
            agent = request.user.agent_profile
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update allowed fields
        if 'languages' in request.data:
            agent.languages = request.data['languages']
        if 'specializations' in request.data:
            agent.specializations = request.data['specializations']
        if 'working_hours' in request.data:
            agent.working_hours = request.data['working_hours']
        if 'use_ai_assistance' in request.data:
            agent.use_ai_assistance = request.data['use_ai_assistance']
        if 'ai_confidence_threshold' in request.data:
            agent.ai_confidence_threshold = request.data['ai_confidence_threshold']
        if 'preferred_ai_model' in request.data:
            agent.preferred_ai_model = request.data['preferred_ai_model']
        
        agent.save()
        
        return Response({
            'message': 'Profile updated successfully'
        }, status=status.HTTP_200_OK)


class AgentStatusAPIView(APIView):
    """Manage agent status"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    enum=['available', 'busy', 'on_call', 'away', 'offline'],
                    description='New agent status'
                )
            },
            required=['status']
        ),
        responses={
            200: "Status updated successfully",
            400: "Bad request",
            401: "Unauthorized",
            404: "Agent profile not found"
        },
        operation_description="Update agent status",
        tags=['AI Agents'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        new_status = request.data.get('status')
        
        if not new_status or new_status not in ['available', 'busy', 'on_call', 'away', 'offline']:
            return Response({
                'error': 'Valid status is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            agent = request.user.agent_profile
            agent.status = new_status
            agent.last_activity = timezone.now()
            agent.save()
            
            return Response({
                'message': 'Status updated successfully',
                'status': agent.status
            }, status=status.HTTP_200_OK)
            
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AgentPerformanceAPIView(APIView):
    """Get agent performance statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('days', openapi.IN_QUERY, description="Number of days to get performance for", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: "Agent performance data",
            401: "Unauthorized",
            404: "Agent profile not found"
        },
        operation_description="Get agent performance statistics",
        tags=['AI Agents'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            agent = request.user.agent_profile
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Get performance data for the period
        performance_data = AgentPerformance.objects.filter(
            agent=agent,
            date__gte=start_date
        ).order_by('date')
        
        # Calculate totals
        total_calls = sum(p.total_calls for p in performance_data)
        total_completed = sum(p.completed_calls for p in performance_data)
        avg_talk_time = sum(p.average_talk_time for p in performance_data) / len(performance_data) if performance_data else 0
        avg_satisfaction = sum(p.customer_satisfaction for p in performance_data) / len(performance_data) if performance_data else 0
        
        # Daily breakdown
        daily_performance = []
        for performance in performance_data:
            daily_performance.append({
                'date': performance.date.isoformat(),
                'total_calls': performance.total_calls,
                'completed_calls': performance.completed_calls,
                'avg_talk_time': performance.average_talk_time,
                'customer_satisfaction': performance.customer_satisfaction,
                'success_rate': (performance.completed_calls / performance.total_calls * 100) if performance.total_calls > 0 else 0
            })
        
        response_data = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': timezone.now().date().isoformat(),
                'days': days
            },
            'summary': {
                'total_calls': total_calls,
                'completed_calls': total_completed,
                'success_rate': (total_completed / total_calls * 100) if total_calls > 0 else 0,
                'average_talk_time': avg_talk_time,
                'customer_satisfaction': avg_satisfaction
            },
            'daily_performance': daily_performance,
            'current_metrics': {
                'total_calls': agent.total_calls,
                'successful_calls': agent.successful_calls,
                'success_rate': agent.success_rate,
                'average_call_duration': agent.average_call_duration,
                'customer_satisfaction': agent.customer_satisfaction
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class AgentCallHistoryAPIView(APIView):
    """Get agent call history"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by call status", type=openapi.TYPE_STRING),
        ],
        responses={
            200: "Agent call history",
            401: "Unauthorized",
            404: "Agent profile not found"
        },
        operation_description="Get agent call history with pagination",
        tags=['AI Agents'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            agent = request.user.agent_profile
        except Agent.DoesNotExist:
            return Response({
                'error': 'Agent profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Filter parameters
        status_filter = request.query_params.get('status')
        page = int(request.query_params.get('page', 1))
        limit = 20
        offset = (page - 1) * limit
        
        # Base queryset
        calls = CallSession.objects.filter(agent=agent).order_by('-started_at')
        
        # Apply status filter
        if status_filter:
            calls = calls.filter(status=status_filter)
        
        # Get total count and paginate
        total_count = calls.count()
        calls = calls[offset:offset + limit]
        
        call_data = []
        for call in calls:
            call_data.append({
                'id': str(call.id),
                'call_type': call.call_type,
                'phone_number': call.phone_number,
                'status': call.status,
                'started_at': call.started_at.isoformat(),
                'ended_at': call.ended_at.isoformat() if call.ended_at else None,
                'duration': call.call_duration_formatted,
                'customer_satisfaction': call.customer_satisfaction,
                'ai_transcript': call.ai_transcript[:200] + '...' if call.ai_transcript and len(call.ai_transcript) > 200 else call.ai_transcript,
                'recording_url': call.recording_url,
                'user': {
                    'id': str(call.user.id),
                    'name': call.user.get_full_name(),
                    'email': call.user.email
                } if call.user else None
            })
        
        return Response({
            'calls': call_data,
            'pagination': {
                'current_page': page,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit,
                'per_page': limit
            }
        }, status=status.HTTP_200_OK)
