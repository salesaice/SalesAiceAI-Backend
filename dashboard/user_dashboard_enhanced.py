from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from subscriptions.models import Subscription, SubscriptionPlan
from calls.models import CallSession
from agents.models import Agent
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

User = get_user_model()


class UserDashboardAPIView(APIView):
    """
    User Dashboard API - matches image requirements
    Shows inbound, outbound, total calls + quick actions
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Dashboard'],
        operation_summary="User Dashboard Enhanced",
        operation_description="Get user dashboard with call statistics, quick actions, subscription info, and AI agent status",
        responses={
            200: "User dashboard data retrieved successfully",
            401: "Unauthorized - Authentication required"
        }
    )
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_week = timezone.now() - timedelta(days=7)
        
        # 1. USER PROFILE & SUBSCRIPTION INFO
        try:
            subscription = user.subscription
            subscription_info = {
                'status': 'active' if subscription.is_active else 'inactive',
                'plan_name': subscription.plan.name,
                'minutes_used': subscription.minutes_used_this_month,
                'minutes_limit': subscription.plan.call_minutes_limit,
                'usage_percentage': subscription.usage_percentage,
                'expires_at': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                'package_features': {
                    'agents_allowed': subscription.plan.agents_allowed,
                    'call_minutes_limit': subscription.plan.call_minutes_limit,
                    'analytics_access': subscription.plan.analytics_access,
                    'advanced_analytics': subscription.plan.advanced_analytics
                }
            }
        except Subscription.DoesNotExist:
            subscription_info = {
                'status': 'no_subscription',
                'message': 'Please select a subscription package',
                'setup_required': True
            }
        
        # 2. CALL STATISTICS (Main requirement - inbound, outbound, total)
        user_calls = CallSession.objects.filter(user=user)
        
        # Total call counts
        total_calls = user_calls.count()
        inbound_calls = user_calls.filter(call_type='inbound').count()
        outbound_calls = user_calls.filter(call_type='outbound').count()
        
        # Today's calls
        calls_today = user_calls.filter(started_at__date=today).count()
        inbound_today = user_calls.filter(started_at__date=today, call_type='inbound').count()
        outbound_today = user_calls.filter(started_at__date=today, call_type='outbound').count()
        
        # This month's calls
        calls_this_month = user_calls.filter(started_at__gte=this_month).count()
        inbound_this_month = user_calls.filter(started_at__gte=this_month, call_type='inbound').count()
        outbound_this_month = user_calls.filter(started_at__gte=this_month, call_type='outbound').count()
        
        # Success statistics
        successful_calls = user_calls.filter(
            status__in=['completed', 'answered']
        ).count()
        completed_calls = user_calls.filter(status='completed').count()
        
        # Calculate rates
        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        completion_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        
        call_statistics = {
            'total_calls': total_calls,
            'inbound_calls': inbound_calls,
            'outbound_calls': outbound_calls,
            'today': {
                'total': calls_today,
                'inbound': inbound_today,
                'outbound': outbound_today
            },
            'this_month': {
                'total': calls_this_month,
                'inbound': inbound_this_month,
                'outbound': outbound_this_month
            },
            'success_metrics': {
                'successful_calls': successful_calls,
                'completed_calls': completed_calls,
                'success_rate': round(success_rate, 1),
                'completion_rate': round(completion_rate, 1)
            },
            'call_breakdown': {
                'inbound_percentage': round((inbound_calls / total_calls * 100), 1) if total_calls > 0 else 0,
                'outbound_percentage': round((outbound_calls / total_calls * 100), 1) if total_calls > 0 else 0
            }
        }
        
        # 3. AI AGENT STATUS
        agent_status = None
        try:
            # Get user's first agent (new model structure)
            agent = Agent.objects.filter(user=user, agent_type='inbound').first()
            if agent:
                agent_status = {
                    'id': str(agent.id),
                    'name': agent.name,
                    'status': agent.status,
                    'agent_type': agent.agent_type,
                    'calls_handled': 0,  # Will be calculated from performance metrics
                    'is_ready': agent.status == 'active'
                }
            else:
                raise Agent.DoesNotExist()
        except Agent.DoesNotExist:
            agent_status = {
                'status': 'no_agent',
                'message': 'No AI agent created yet',
                'setup_required': True
            }
        
        # 4. QUICK ACTIONS (7 actions as per image)
        quick_actions = [
            {
                'id': 'start_outbound_call',
                'title': 'Start Outbound Call',
                'description': 'Make a new outbound call to prospects',
                'icon': 'phone-outgoing',
                'color': 'blue',
                'enabled': subscription_info.get('status') == 'active',
                'url': '/api/calls/start-outbound/',
                'action_type': 'primary'
            },
            {
                'id': 'manage_contacts',
                'title': 'Manage Contacts',
                'description': 'Upload and manage customer contacts',
                'icon': 'users',
                'color': 'green',
                'enabled': True,
                'url': '/api/agents/contacts/upload/',
                'action_type': 'secondary'
            },
            {
                'id': 'configure_agent',
                'title': 'Configure AI Agent',
                'description': 'Set up and train your AI sales agent',
                'icon': 'bot',
                'color': 'purple',
                'enabled': True,
                'url': '/api/agents/management/create/',
                'action_type': 'secondary'
            },
            {
                'id': 'view_analytics',
                'title': 'View Analytics',
                'description': 'Detailed call analytics and insights',
                'icon': 'bar-chart',
                'color': 'orange',
                'enabled': subscription_info.get('package_features', {}).get('analytics_access', False),
                'url': '/api/dashboard/analytics/',
                'action_type': 'secondary'
            },
            {
                'id': 'schedule_campaigns',
                'title': 'Schedule Campaigns',
                'description': 'Plan and schedule calling campaigns',
                'icon': 'calendar',
                'color': 'indigo',
                'enabled': subscription_info.get('status') == 'active',
                'url': '/api/agents/campaigns/schedule/',
                'action_type': 'secondary'
            },
            {
                'id': 'upgrade_subscription',
                'title': 'Upgrade Plan',
                'description': 'Upgrade your subscription for more features',
                'icon': 'arrow-up',
                'color': 'yellow',
                'enabled': subscription_info.get('status') != 'no_subscription',
                'url': '/api/subscriptions/upgrade/',
                'action_type': 'secondary'
            },
            {
                'id': 'support_help',
                'title': 'Get Support',
                'description': 'Contact support or view help documentation',
                'icon': 'help-circle',
                'color': 'gray',
                'enabled': True,
                'url': '/api/support/contact/',
                'action_type': 'secondary'
            }
        ]
        
        # 5. RECENT CALL HISTORY (Last 5 calls)
        recent_calls = []
        latest_calls = user_calls.order_by('-started_at')[:5]
        
        for call in latest_calls:
            recent_calls.append({
                'id': str(call.id),
                'phone_number': call.callee_number or call.caller_number,
                'call_type': call.call_type,
                'status': call.status,
                'duration': call.duration,
                'duration_formatted': call.call_duration_formatted,
                'started_at': call.started_at.isoformat(),
                'ai_sentiment': call.ai_sentiment or 'neutral',
                'notes': call.notes[:100] + '...' if len(call.notes) > 100 else call.notes
            })
        
        # 6. USAGE ALERTS & NOTIFICATIONS
        notifications = []
        
        if subscription_info.get('status') == 'no_subscription':
            notifications.append({
                'type': 'warning',
                'title': 'No Active Subscription',
                'message': 'Please subscribe to a plan to start making calls',
                'action': 'Choose Plan',
                'url': '/api/subscriptions/packages/'
            })
        elif subscription_info.get('usage_percentage', 0) > 80:
            notifications.append({
                'type': 'warning',
                'title': 'High Usage Alert',
                'message': f"You've used {subscription_info.get('usage_percentage', 0)}% of your monthly minutes",
                'action': 'Upgrade Plan',  
                'url': '/api/subscriptions/upgrade/'
            })
        
        if agent_status and agent_status.get('setup_required'):
            notifications.append({
                'type': 'info',
                'title': 'AI Agent Setup Required',
                'message': 'Create and configure your AI agent to start automated calling',
                'action': 'Setup Agent',
                'url': '/api/agents/management/create/'
            })
        
        # 7. DASHBOARD SUMMARY
        dashboard_summary = {
            'account_status': 'active' if subscription_info.get('status') == 'active' else 'setup_required',
            'total_calls_made': total_calls,
            'calls_today': calls_today,
            'success_rate': success_rate,
            'agent_ready': agent_status.get('is_ready', False) if agent_status else False,
            'subscription_active': subscription_info.get('status') == 'active',
            'needs_attention': len(notifications) > 0
        }
        
        # Final Response
        user_dashboard = {
            'user_profile': {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.get_full_name(),
                'role': user.role,
                'avatar': user.avatar.url if user.avatar else None
            },
            'subscription_info': subscription_info,
            'call_statistics': call_statistics,
            'agent_status': agent_status,
            'quick_actions': quick_actions,
            'recent_calls': recent_calls,
            'notifications': notifications,
            'dashboard_summary': dashboard_summary
        }
        
        return Response(user_dashboard, status=status.HTTP_200_OK)
