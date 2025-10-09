from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Avg, Sum
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timedelta

from agents.ai_agent_models import (
    AIAgent, CustomerProfile, CallSession, 
    AIAgentTraining, ScheduledCallback
)

User = get_user_model()


class AIAgentDashboardAPIView(APIView):
    """
    Complete AI Agent Dashboard for Client
    Client ka complete AI agent dashboard - sab kuch ek jagah
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: "Complete AI Agent dashboard data",
            404: "AI Agent not found"
        },
        operation_description="Get complete AI Agent dashboard - agent status, performance, calls, learning",
        tags=['Dashboard']
    )
    def get(self, request):
        user = request.user
        
        try:
            agent = user.ai_agent
        except AIAgent.DoesNotExist:
            return Response({
                'error': 'No AI Agent found for this client',
                'message': 'Please create an AI Agent first',
                'setup_url': '/api/agents/ai/setup/'
            }, status=status.HTTP_404_NOT_FOUND)
        
        today = timezone.now().date()
        this_month = timezone.now().replace(day=1)
        
        # 1. AGENT STATUS & BASIC INFO
        agent_info = {
            'id': str(agent.id),
            'name': agent.name,
            'status': agent.status,
            'personality_type': agent.personality_type,
            'training_level': agent.training_level,
            'is_ready_for_calls': agent.is_ready_for_calls,
            'created_at': agent.created_at.isoformat(),
            'working_hours': {
                'start': agent.working_hours_start.strftime('%H:%M'),
                'end': agent.working_hours_end.strftime('%H:%M')
            }
        }
        
        # 2. PERFORMANCE METRICS
        performance = {
            'total_calls_handled': agent.calls_handled,
            'successful_conversions': agent.successful_conversions,
            'conversion_rate': agent.conversion_rate,
            'avg_call_duration': agent.avg_call_duration,
            'customer_satisfaction': agent.customer_satisfaction,
            'today_calls': CallSession.objects.filter(
                ai_agent=agent,
                initiated_at__date=today
            ).count(),
            'this_month_calls': CallSession.objects.filter(
                ai_agent=agent,
                initiated_at__gte=this_month
            ).count()
        }
        
        # 3. RECENT CALLS
        recent_calls = CallSession.objects.filter(
            ai_agent=agent
        ).order_by('-initiated_at')[:10]
        
        calls_data = []
        for call in recent_calls:
            calls_data.append({
                'id': str(call.id),
                'phone_number': call.phone_number,
                'call_type': call.call_type,
                'outcome': call.outcome,
                'duration': call.duration_formatted,
                'initiated_at': call.initiated_at.isoformat(),
                'customer_name': call.customer_profile.name if call.customer_profile.name else 'Unknown',
                'interest_level': call.customer_profile.interest_level,
                'followup_scheduled': call.followup_scheduled
            })
        
        # 4. CUSTOMER PROFILES
        customers = CustomerProfile.objects.filter(ai_agent=agent)
        customer_stats = {
            'total_customers': customers.count(),
            'hot_leads': customers.filter(interest_level='hot').count(),
            'warm_leads': customers.filter(interest_level='warm').count(),
            'cold_leads': customers.filter(interest_level='cold').count(),
            'converted': customers.filter(is_converted=True).count(),
            'do_not_call': customers.filter(is_do_not_call=True).count()
        }
        
        # Recent customers
        recent_customers = customers.order_by('-created_at')[:5]
        customers_data = []
        for customer in recent_customers:
            customers_data.append({
                'id': str(customer.id),
                'phone_number': customer.phone_number,
                'name': customer.name or 'Unknown',
                'interest_level': customer.interest_level,
                'total_calls': customer.total_calls,
                'last_interaction': customer.last_interaction.isoformat() if customer.last_interaction else None,
                'is_converted': customer.is_converted
            })
        
        # 5. SCHEDULED CALLBACKS
        upcoming_callbacks = ScheduledCallback.objects.filter(
            ai_agent=agent,
            status='scheduled',
            scheduled_datetime__gte=timezone.now()
        ).order_by('scheduled_datetime')[:10]
        
        callbacks_data = []
        for callback in upcoming_callbacks:
            callbacks_data.append({
                'id': str(callback.id),
                'customer_phone': callback.customer_profile.phone_number,
                'customer_name': callback.customer_profile.name,
                'scheduled_datetime': callback.scheduled_datetime.isoformat(),
                'reason': callback.reason,
                'priority_level': callback.priority_level,
                'customer_interest': callback.customer_profile.interest_level
            })
        
        # 6. TRAINING STATUS
        training_sessions = AIAgentTraining.objects.filter(
            ai_agent=agent
        ).order_by('-created_at')
        
        training_data = {
            'total_sessions': training_sessions.count(),
            'completed_sessions': training_sessions.filter(is_completed=True).count(),
            'training_types': list(training_sessions.values('training_type').annotate(
                count=Count('id')
            )),
            'latest_training': None
        }
        
        if training_sessions.exists():
            latest = training_sessions.first()
            training_data['latest_training'] = {
                'type': latest.training_type,
                'completion': latest.completion_percentage,
                'is_completed': latest.is_completed,
                'created_at': latest.created_at.isoformat()
            }
        
        # 7. QUICK ACTIONS FOR CLIENT
        quick_actions = [
            {
                'id': 'train_agent',
                'title': 'Train Agent',
                'description': 'Provide additional training to your AI agent',
                'icon': 'graduation-cap',
                'enabled': True,
                'url': '/api/agents/ai/training/'
            },
            {
                'id': 'start_outbound_call',
                'title': 'Start Outbound Call',
                'description': 'Make an AI-powered outbound call',
                'icon': 'phone-outgoing',
                'enabled': agent.is_ready_for_calls,
                'url': '/api/agents/ai/start-call/'
            },
            {
                'id': 'view_customers',
                'title': 'Customer Profiles',
                'description': 'View and manage customer profiles',
                'icon': 'users',
                'enabled': True,
                'url': '/api/agents/ai/customers/'
            },
            {
                'id': 'schedule_callbacks',
                'title': 'Scheduled Callbacks',
                'description': 'Manage scheduled callbacks',
                'icon': 'calendar',
                'enabled': True,
                'url': '/api/agents/ai/callbacks/'
            }
        ]
        
        # 8. LEARNING INSIGHTS
        learning_insights = []
        
        # Get insights from agent's memory
        memory = agent.conversation_memory
        if 'learning_insights' in memory:
            recent_insights = memory['learning_insights'][-5:]  # Last 5 insights
            for insight in recent_insights:
                learning_insights.append({
                    'timestamp': insight.get('timestamp'),
                    'type': 'call_outcome',
                    'outcome': insight.get('call_outcome'),
                    'insight': insight.get('improvement_notes', 'Call completed'),
                    'customer_response': insight.get('customer_response', '')[:100] + '...' if insight.get('customer_response', '') else ''
                })
        
        # 9. ALERTS & NOTIFICATIONS
        alerts = []
        
        # Training level alerts
        if agent.training_level < 20:
            alerts.append({
                'type': 'warning',
                'title': 'Agent Training Incomplete',
                'message': f'Your AI agent is only {agent.training_level}% trained. Complete training to enable calls.',
                'action_text': 'Continue Training',
                'action_url': '/api/agents/ai/training/'
            })
        
        # Callback alerts
        overdue_callbacks = ScheduledCallback.objects.filter(
            ai_agent=agent,
            status='scheduled',
            scheduled_datetime__lt=timezone.now()
        ).count()
        
        if overdue_callbacks > 0:
            alerts.append({
                'type': 'info',
                'title': 'Overdue Callbacks',
                'message': f'You have {overdue_callbacks} overdue callbacks to handle.',
                'action_text': 'View Callbacks',
                'action_url': '/api/agents/ai/callbacks/'
            })
        
        # Performance alerts
        if agent.calls_handled >= 10 and agent.conversion_rate < 10:
            alerts.append({
                'type': 'warning',
                'title': 'Low Conversion Rate',
                'message': f'Your conversion rate is {agent.conversion_rate:.1f}%. Consider additional training.',
                'action_text': 'Improve Training',
                'action_url': '/api/agents/ai/training/'
            })
        
        # 10. CALL STATISTICS BREAKDOWN
        call_stats = {
            'by_outcome': list(CallSession.objects.filter(ai_agent=agent).values('outcome').annotate(count=Count('id'))),
            'by_type': list(CallSession.objects.filter(ai_agent=agent).values('call_type').annotate(count=Count('id'))),
            'this_week': CallSession.objects.filter(
                ai_agent=agent,
                initiated_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            'avg_duration_today': CallSession.objects.filter(
                ai_agent=agent,
                initiated_at__date=today,
                duration_seconds__gt=0
            ).aggregate(avg=Avg('duration_seconds'))['avg'] or 0
        }
        
        dashboard_data = {
            'agent_info': agent_info,
            'performance': performance,
            'recent_calls': calls_data,
            'customer_stats': customer_stats,
            'recent_customers': customers_data,
            'upcoming_callbacks': callbacks_data,
            'training_status': training_data,
            'quick_actions': quick_actions,
            'learning_insights': learning_insights,
            'alerts': alerts,
            'call_statistics': call_stats,
            'summary': {
                'agent_ready': agent.is_ready_for_calls,
                'calls_today': performance['today_calls'],
                'pending_callbacks': len(callbacks_data),
                'conversion_trend': 'improving' if agent.conversion_rate > 15 else 'needs_attention'
            }
        }
        
        return Response(dashboard_data, status=status.HTTP_200_OK)


class CustomerProfilesAPIView(APIView):
    """
    Manage customer profiles for AI Agent
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('interest_level', openapi.IN_QUERY, description="Filter by interest level", type=openapi.TYPE_STRING),
            openapi.Parameter('converted', openapi.IN_QUERY, description="Filter by conversion status", type=openapi.TYPE_BOOLEAN),
        ],
        responses={200: "Customer profiles list"},
        tags=['AI Agents']
    )
    def get(self, request):
        try:
            agent = request.user.ai_agent
            
            customers = CustomerProfile.objects.filter(ai_agent=agent)
            
            # Apply filters
            interest_level = request.query_params.get('interest_level')
            converted = request.query_params.get('converted')
            
            if interest_level:
                customers = customers.filter(interest_level=interest_level)
            if converted is not None:
                customers = customers.filter(is_converted=converted.lower() == 'true')
            
            customers = customers.order_by('-last_interaction', '-created_at')
            
            customers_data = []
            for customer in customers:
                customers_data.append({
                    'id': str(customer.id),
                    'phone_number': customer.phone_number,
                    'name': customer.name or 'Unknown',
                    'email': customer.email,
                    'interest_level': customer.interest_level,
                    'total_calls': customer.total_calls,
                    'successful_calls': customer.successful_calls,
                    'last_interaction': customer.last_interaction.isoformat() if customer.last_interaction else None,
                    'next_followup': customer.next_followup.isoformat() if customer.next_followup else None,
                    'is_converted': customer.is_converted,
                    'conversion_date': customer.conversion_date.isoformat() if customer.conversion_date else None,
                    'communication_style': customer.communication_style,
                    'call_preference_time': customer.call_preference_time,
                    'is_do_not_call': customer.is_do_not_call
                })
            
            return Response({
                'customers': customers_data,
                'total_count': len(customers_data),
                'summary': {
                    'total': customers.count(),
                    'hot_leads': customers.filter(interest_level='hot').count(),
                    'converted': customers.filter(is_converted=True).count(),
                    'do_not_call': customers.filter(is_do_not_call=True).count()
                }
            }, status=status.HTTP_200_OK)
            
        except AIAgent.DoesNotExist:
            return Response({
                'error': 'No AI Agent found'
            }, status=status.HTTP_404_NOT_FOUND)


class ScheduledCallbacksAPIView(APIView):
    """
    Manage scheduled callbacks for AI Agent
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status", type=openapi.TYPE_STRING),
            openapi.Parameter('overdue', openapi.IN_QUERY, description="Show only overdue callbacks", type=openapi.TYPE_BOOLEAN),
        ],
        responses={200: "Scheduled callbacks list"},
        tags=['AI Agents']
    )
    def get(self, request):
        try:
            agent = request.user.ai_agent
            
            callbacks = ScheduledCallback.objects.filter(ai_agent=agent)
            
            # Apply filters
            status_filter = request.query_params.get('status')
            overdue = request.query_params.get('overdue')
            
            if status_filter:
                callbacks = callbacks.filter(status=status_filter)
            if overdue and overdue.lower() == 'true':
                callbacks = callbacks.filter(
                    status='scheduled',
                    scheduled_datetime__lt=timezone.now()
                )
            
            callbacks = callbacks.order_by('scheduled_datetime')
            
            callbacks_data = []
            for callback in callbacks:
                callbacks_data.append({
                    'id': str(callback.id),
                    'customer': {
                        'phone_number': callback.customer_profile.phone_number,
                        'name': callback.customer_profile.name,
                        'interest_level': callback.customer_profile.interest_level
                    },
                    'scheduled_datetime': callback.scheduled_datetime.isoformat(),
                    'reason': callback.reason,
                    'notes': callback.notes,
                    'status': callback.status,
                    'priority_level': callback.priority_level,
                    'expected_outcome': callback.expected_outcome,
                    'is_overdue': callback.scheduled_datetime < timezone.now() and callback.status == 'scheduled',
                    'created_at': callback.created_at.isoformat()
                })
            
            return Response({
                'callbacks': callbacks_data,
                'total_count': len(callbacks_data),
                'summary': {
                    'scheduled': callbacks.filter(status='scheduled').count(),
                    'completed': callbacks.filter(status='completed').count(),
                    'overdue': callbacks.filter(
                        status='scheduled',
                        scheduled_datetime__lt=timezone.now()
                    ).count()
                }
            }, status=status.HTTP_200_OK)
            
        except AIAgent.DoesNotExist:
            return Response({
                'error': 'No AI Agent found'
            }, status=status.HTTP_404_NOT_FOUND)
