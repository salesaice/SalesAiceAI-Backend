from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from accounts.permissions import IsAdmin
from subscriptions.models import Subscription, BillingHistory, UsageMetrics
from calls.models import CallSession, CallQueue, QuickAction
from agents.models import Agent, AgentPerformance
from .models import DashboardWidget, SystemNotification, ActivityLog

User = get_user_model()


class DashboardStatsAPIView(APIView):
    """Get dashboard statistics based on user role"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: "Dashboard statistics",
            401: "Unauthorized"
        },
        operation_description="Get dashboard statistics based on user role",
        tags=['Dashboard'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        if user.role == 'admin':
            return self.get_admin_stats(request)
        elif user.role == 'agent':
            return self.get_agent_stats(request)
        else:
            return self.get_user_stats(request)
    
    def get_admin_stats(self, request):
        """Admin dashboard statistics with detailed breakdown"""
        today = timezone.now().date()
        this_month = timezone.now().replace(day=1)
        
        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        users_by_role = User.objects.values('role').annotate(count=Count('id'))
        
        # Subscription statistics
        subscription_stats = Subscription.objects.values('status').annotate(count=Count('id'))
        active_subscriptions = Subscription.objects.filter(status='active').count()
        total_subscriptions = Subscription.objects.count()
        
        # Subscription plans breakdown
        plan_breakdown = Subscription.objects.filter(status='active').values(
            'plan__name', 'plan__price'
        ).annotate(count=Count('id'))
        
        # Agent statistics
        total_agents = Agent.objects.filter(is_active=True).count()
        agents_by_status = Agent.objects.values('status').annotate(count=Count('id'))
        online_agents = Agent.objects.filter(status__in=['available', 'busy', 'on_call']).count()
        
        # Call statistics
        today_calls = CallSession.objects.filter(started_at__date=today).count()
        total_calls = CallSession.objects.count()
        calls_by_status = CallSession.objects.values('status').annotate(count=Count('id'))
        active_calls = CallSession.objects.filter(status='answered').count()
        queued_calls = CallQueue.objects.filter(status='waiting').count()
        
        # Revenue statistics
        monthly_revenue = BillingHistory.objects.filter(
            created_at__gte=this_month,
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_revenue = BillingHistory.objects.filter(
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Recent subscriptions
        recent_subscriptions = []
        recent_subs = Subscription.objects.select_related('user', 'plan').order_by('-created_at')[:5]
        for sub in recent_subs:
            recent_subscriptions.append({
                'id': str(sub.id),
                'user_name': f"{sub.user.first_name} {sub.user.last_name}".strip() or sub.user.email,
                'user_email': sub.user.email,
                'plan_name': sub.plan.name,
                'status': sub.status,
                'created_at': sub.created_at.isoformat(),
                'amount': float(sub.plan.price)
            })
        
        data = {
            'overview': {
                'total_users': total_users,
                'active_users': active_users,
                'total_subscriptions': total_subscriptions,
                'active_subscriptions': active_subscriptions,
                'total_agents': total_agents,
                'online_agents': online_agents,
                'today_calls': today_calls,
                'total_calls': total_calls,
                'active_calls': active_calls,
                'queued_calls': queued_calls,
                'monthly_revenue': float(monthly_revenue),
                'total_revenue': float(total_revenue),
                'agent_utilization': (online_agents / total_agents * 100) if total_agents > 0 else 0
            },
            'breakdown': {
                'users_by_role': {item['role']: item['count'] for item in users_by_role},
                'subscriptions_by_status': {item['status']: item['count'] for item in subscription_stats},
                'agents_by_status': {item['status']: item['count'] for item in agents_by_status},
                'calls_by_status': {item['status']: item['count'] for item in calls_by_status},
                'subscription_plans': list(plan_breakdown)
            },
            'recent_subscriptions': recent_subscriptions
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    def get_agent_stats(self, request):
        """Agent dashboard statistics"""
        try:
            agent = request.user.agent_profile
        except Agent.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        today = timezone.now().date()
        
        # Today's performance
        today_calls = CallSession.objects.filter(
            agent=agent,
            started_at__date=today
        ).count()
        
        completed_calls = CallSession.objects.filter(
            agent=agent,
            started_at__date=today,
            status='completed'
        ).count()
        
        # Average call duration today
        avg_duration = CallSession.objects.filter(
            agent=agent,
            started_at__date=today,
            status='completed'
        ).aggregate(avg=Avg('duration'))['avg'] or 0
        
        # Queue status
        queued_calls = CallQueue.objects.filter(status='waiting').count()
        my_queue = CallQueue.objects.filter(assigned_agent=agent, status='waiting').count()
        
        data = {
            'agent_status': agent.status,
            'today_calls': today_calls,
            'completed_calls': completed_calls,
            'avg_call_duration': round(avg_duration / 60, 2) if avg_duration else 0,  # in minutes
            'success_rate': agent.success_rate,
            'queued_calls': queued_calls,
            'my_queue': my_queue,
            'customer_satisfaction': agent.customer_satisfaction
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    def get_user_stats(self, request):
        """User dashboard statistics"""
        user = request.user
        
        try:
            subscription = user.subscription
            current_usage = UsageMetrics.objects.filter(
                subscription=subscription,
                date=timezone.now().date()
            ).first()
            
            # Billing information
            last_payment = BillingHistory.objects.filter(
                subscription=subscription,
                status='paid'
            ).order_by('-created_at').first()
            
            data = {
                'subscription_status': subscription.status,
                'subscription_plan': subscription.plan.name,
                'days_remaining': subscription.days_remaining,
                'minutes_used': subscription.minutes_used,
                'minutes_limit': subscription.plan.max_minutes,
                'usage_percentage': (subscription.minutes_used / subscription.plan.max_minutes * 100) if subscription.plan.max_minutes > 0 else 0,
                'next_billing_date': subscription.next_billing_date.isoformat(),
                'last_payment_amount': float(last_payment.amount) if last_payment else 0,
                'today_calls': current_usage.inbound_calls + current_usage.outbound_calls if current_usage else 0
            }
            
        except Subscription.DoesNotExist:
            data = {
                'subscription_status': 'none',
                'subscription_plan': 'No Plan',
                'days_remaining': 0,
                'minutes_used': 0,
                'minutes_limit': 0,
                'usage_percentage': 0,
                'next_billing_date': None,
                'last_payment_amount': 0,
                'today_calls': 0
            }
        
        return Response(data, status=status.HTTP_200_OK)


class QuickActionsAPIView(APIView):
    """Get quick actions for dashboard"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: "Quick actions data",
            401: "Unauthorized"
        },
        operation_description="Get quick actions for dashboard",
        tags=['Dashboard'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        # Default quick actions
        default_actions = [
            {
                'id': 'inbound_call',
                'name': 'Inbound Call',
                'action_type': 'call',
                'icon': 'phone-incoming',
                'color': 'success',
                'config': {'type': 'inbound'}
            },
            {
                'id': 'outbound_call',
                'name': 'Outbound Call',
                'action_type': 'call',
                'icon': 'phone-outgoing',
                'color': 'primary',
                'config': {'type': 'outbound'}
            },
            {
                'id': 'send_sms',
                'name': 'Send SMS',
                'action_type': 'sms',
                'icon': 'message-circle',
                'color': 'info',
                'config': {}
            },
            {
                'id': 'schedule_callback',
                'name': 'Schedule Callback',
                'action_type': 'schedule',
                'icon': 'calendar',
                'color': 'warning',
                'config': {}
            }
        ]
        
        return Response(default_actions, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'action': openapi.Schema(type=openapi.TYPE_STRING, description='Action type'),
            'data': openapi.Schema(type=openapi.TYPE_OBJECT, description='Action data')
        }
    ),
    responses={200: "Action executed successfully"},
    operation_description="Execute quick action",
    tags=['Dashboard'],
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def execute_quick_action(request):
    """Execute a quick action"""
    action = request.data.get('action')
    data = request.data.get('data', {})
    
    if action == 'inbound_call':
        # Handle inbound call setup
        return Response({
            'message': 'Inbound call initiated',
            'call_id': 'sample-call-id'
        }, status=status.HTTP_200_OK)
    
    elif action == 'outbound_call':
        # Handle outbound call setup
        phone_number = data.get('phone_number')
        if not phone_number:
            return Response({
                'error': 'Phone number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'message': f'Outbound call initiated to {phone_number}',
            'call_id': 'sample-call-id'
        }, status=status.HTTP_200_OK)
    
    elif action == 'send_sms':
        # Handle SMS sending
        return Response({
            'message': 'SMS sent successfully'
        }, status=status.HTTP_200_OK)
    
    elif action == 'add_note':
        # Handle note creation
        return Response({
            'message': 'Note added successfully'
        }, status=status.HTTP_200_OK)
    
    else:
        return Response({
            'error': 'Unknown action'
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminSubscriptionsAPIView(APIView):
    """Get all subscriptions for admin"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status", type=openapi.TYPE_STRING),
            openapi.Parameter('plan', openapi.IN_QUERY, description="Filter by plan type", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: "List of all subscriptions",
            403: "Forbidden - Admin access required"
        },
        operation_description="Get all subscriptions with filtering (Admin only)",
        tags=['Dashboard'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        # Filter parameters
        status_filter = request.query_params.get('status')
        plan_filter = request.query_params.get('plan')
        
        # Base queryset
        subscriptions = Subscription.objects.select_related('user', 'plan').all()
        
        # Apply filters
        if status_filter:
            subscriptions = subscriptions.filter(status=status_filter)
        if plan_filter:
            subscriptions = subscriptions.filter(plan__plan_type=plan_filter)
        
        # Order by creation date
        subscriptions = subscriptions.order_by('-created_at')
        
        # Pagination (simple limit/offset)
        page = int(request.query_params.get('page', 1))
        limit = 20
        offset = (page - 1) * limit
        total_count = subscriptions.count()
        subscriptions = subscriptions[offset:offset + limit]
        
        data = []
        for sub in subscriptions:
            data.append({
                'id': str(sub.id),
                'user': {
                    'id': str(sub.user.id),
                    'name': f"{sub.user.first_name} {sub.user.last_name}".strip() or sub.user.email,
                    'email': sub.user.email,
                    'role': sub.user.role
                },
                'plan': {
                    'name': sub.plan.name,
                    'type': sub.plan.plan_type,
                    'price': float(sub.plan.price),
                    'billing_cycle': sub.plan.billing_cycle,
                    'max_agents': sub.plan.max_agents,
                    'max_minutes': sub.plan.max_minutes
                },
                'status': sub.status,
                'start_date': sub.start_date.isoformat(),
                'end_date': sub.end_date.isoformat(),
                'next_billing_date': sub.next_billing_date.isoformat(),
                'minutes_used': sub.minutes_used,
                'agents_used': sub.agents_used,
                'days_remaining': sub.days_remaining,
                'usage_percentage': (sub.minutes_used / sub.plan.max_minutes * 100) if sub.plan.max_minutes > 0 else 0,
                'created_at': sub.created_at.isoformat(),
                'stripe_subscription_id': sub.stripe_subscription_id
            })
        
        return Response({
            'subscriptions': data,
            'pagination': {
                'current_page': page,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit,
                'per_page': limit
            }
        }, status=status.HTTP_200_OK)


class AdminAgentsAPIView(APIView):
    """Get all agents for admin"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status", type=openapi.TYPE_STRING),
            openapi.Parameter('department', openapi.IN_QUERY, description="Filter by department", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: "List of all agents",
            403: "Forbidden - Admin access required"
        },
        operation_description="Get all agents with filtering and performance data (Admin only)",
        tags=['Dashboard'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        # Filter parameters
        status_filter = request.query_params.get('status')
        department_filter = request.query_params.get('department')
        
        # Base queryset
        agents = Agent.objects.select_related('user').filter(is_active=True)
        
        # Apply filters
        if status_filter:
            agents = agents.filter(status=status_filter)
        if department_filter:
            agents = agents.filter(department=department_filter)
        
        # Order by last activity
        agents = agents.order_by('-last_activity')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        limit = 20
        offset = (page - 1) * limit
        total_count = agents.count()
        agents = agents[offset:offset + limit]
        
        data = []
        today = timezone.now().date()
        
        for agent in agents:
            # Get today's performance
            today_performance = AgentPerformance.objects.filter(
                agent=agent, date=today
            ).first()
            
            # Get recent calls
            recent_calls = CallSession.objects.filter(
                agent=agent
            ).order_by('-started_at')[:5]
            
            agent_data = {
                'id': str(agent.id),
                'user': {
                    'id': str(agent.user.id),
                    'name': f"{agent.user.first_name} {agent.user.last_name}".strip(),
                    'email': agent.user.email
                },
                'employee_id': agent.employee_id,
                'department': agent.department,
                'team': agent.team,
                'status': agent.status,
                'skill_level': agent.skill_level,
                'languages': agent.languages,
                'specializations': agent.specializations,
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
                        'started_at': call.started_at.isoformat()
                    } for call in recent_calls
                ],
                'hired_date': agent.hired_date.isoformat(),
                'created_at': agent.created_at.isoformat()
            }
            
            data.append(agent_data)
        
        return Response({
            'agents': data,
            'pagination': {
                'current_page': page,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit,
                'per_page': limit
            }
        }, status=status.HTTP_200_OK)


class AdminUsersAPIView(APIView):
    """Get all users for admin"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('role', openapi.IN_QUERY, description="Filter by role", type=openapi.TYPE_STRING),
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by active status", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: "List of all users",
            403: "Forbidden - Admin access required"
        },
        operation_description="Get all users with subscription info (Admin only)",
        tags=['Dashboard'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        # Filter parameters
        role_filter = request.query_params.get('role')
        status_filter = request.query_params.get('status')
        
        # Base queryset
        users = User.objects.all()
        
        # Apply filters
        if role_filter:
            users = users.filter(role=role_filter)
        if status_filter is not None:
            users = users.filter(is_active=status_filter.lower() == 'true')
            
        # Order by creation date
        users = users.order_by('-date_joined')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        limit = 20
        offset = (page - 1) * limit
        total_count = users.count()
        users = users[offset:offset + limit]
        
        data = []
        for user in users:
            # Get subscription info
            subscription_info = None
            try:
                sub = user.subscription
                subscription_info = {
                    'plan': sub.plan.name,
                    'status': sub.status,
                    'days_remaining': sub.days_remaining
                }
            except Subscription.DoesNotExist:
                pass
            
            # Get agent info if applicable
            agent_info = None
            if user.role == 'agent':
                try:
                    agent = user.agent_profile
                    agent_info = {
                        'employee_id': agent.employee_id,
                        'department': agent.department,
                        'status': agent.status
                    }
                except Agent.DoesNotExist:
                    pass
            
            user_data = {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'role': user.role,
                'is_active': user.is_active,
                'is_verified': user.is_verified,
                'phone': user.phone,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'subscription': subscription_info,
                'agent_profile': agent_info
            }
            
            data.append(user_data)
        
        return Response({
            'users': data,
            'pagination': {
                'current_page': page,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit,
                'per_page': limit
            }
        }, status=status.HTTP_200_OK)


class UserDashboardOverviewAPIView(APIView):
    """Complete user dashboard overview - sab kuch ek jagah"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: "Complete user dashboard overview",
            401: "Unauthorized"
        },
        operation_description="Get complete user dashboard overview with all management options",
        tags=['Dashboard'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        this_month = timezone.now().replace(day=1)
        
        # 1. USER PROFILE
        user_profile = {
            'id': str(user.id),
            'email': user.email,
            'full_name': user.get_full_name(),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'avatar': user.avatar.url if user.avatar else None,
            'is_verified': user.is_verified,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
        
        # 2. SUBSCRIPTION INFO
        subscription_info = None
        try:
            subscription = user.subscription
            subscription_info = {
                'id': str(subscription.id),
                'plan_name': subscription.plan.name,
                'plan_price': float(subscription.plan.price),
                'status': subscription.status,
                'days_remaining': subscription.days_remaining,
                'current_period_start': subscription.current_period_start.isoformat(),
                'current_period_end': subscription.current_period_end.isoformat(),
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'features': subscription.plan.features,
                'call_limit': subscription.plan.call_limit,
                'agent_limit': subscription.plan.agent_limit
            }
        except Subscription.DoesNotExist:
            subscription_info = {
                'status': 'inactive',
                'message': 'No active subscription. Please choose a plan.'
            }
        
        # 3. CALL STATISTICS
        user_calls = CallSession.objects.filter(user=user)
        total_calls = user_calls.count()
        this_month_calls = user_calls.filter(started_at__gte=this_month).count()
        successful_calls = user_calls.filter(status='completed').count()
        
        call_stats = {
            'total_calls': total_calls,
            'this_month_calls': this_month_calls,
            'successful_calls': successful_calls,
            'success_rate': (successful_calls / total_calls * 100) if total_calls > 0 else 0,
            'calls_remaining': subscription_info.get('call_limit', 0) - this_month_calls if subscription_info.get('call_limit', 0) > 0 else -1
        }
        
        # 4. RECENT CALLS
        recent_calls = user_calls.order_by('-started_at')[:5]
        recent_calls_data = []
        for call in recent_calls:
            recent_calls_data.append({
                'id': str(call.id),
                'phone_number': call.phone_number,
                'call_type': call.call_type,
                'status': call.status,
                'duration': call.call_duration_formatted,
                'started_at': call.started_at.isoformat(),
                'agent': call.agent.user.get_full_name() if call.agent else None,
                'customer_satisfaction': call.customer_satisfaction
            })
        
        # 5. BILLING INFO
        billing_info = None
        if subscription_info and subscription_info.get('status') != 'inactive':
            recent_bills = BillingHistory.objects.filter(
                subscription=user.subscription
            ).order_by('-created_at')[:3]
            
            billing_info = {
                'next_billing_date': subscription_info['current_period_end'],
                'next_amount': subscription_info['plan_price'],
                'recent_payments': [
                    {
                        'id': str(bill.id),
                        'amount': float(bill.amount),
                        'status': bill.status,
                        'created_at': bill.created_at.isoformat(),
                        'description': bill.description
                    } for bill in recent_bills
                ]
            }
        
        # 6. QUICK ACTIONS
        quick_actions = [
            {
                'id': 'start_call',
                'title': 'Start Call',
                'description': 'Make a new call',
                'icon': 'phone',
                'enabled': subscription_info.get('status') == 'active',
                'url': '/api/calls/start-call/'
            },
            {
                'id': 'view_subscription',
                'title': 'Manage Subscription',
                'description': 'View or upgrade your plan',
                'icon': 'credit-card',
                'enabled': True,
                'url': '/api/dashboard/user/subscription-management/'
            },
            {
                'id': 'call_history',
                'title': 'Call History',
                'description': 'View your call records',
                'icon': 'history',
                'enabled': True,
                'url': '/api/dashboard/user/calls/'
            },
            {
                'id': 'account_settings',
                'title': 'Account Settings', 
                'description': 'Manage your account',
                'icon': 'settings',
                'enabled': True,
                'url': '/api/dashboard/user/settings/'
            }
        ]
        
        # 7. NOTIFICATIONS
        notifications = []
        if subscription_info.get('status') == 'inactive':
            notifications.append({
                'type': 'warning',
                'title': 'No Active Subscription',
                'message': 'Subscribe to a plan to start making calls',
                'action_text': 'Choose Plan',
                'action_url': '/api/subscriptions/plans/'
            })
        elif subscription_info.get('days_remaining', 0) <= 3:
            notifications.append({
                'type': 'info',
                'title': 'Subscription Expiring',
                'message': f'Your subscription expires in {subscription_info.get("days_remaining")} days',
                'action_text': 'Renew',
                'action_url': '/api/subscriptions/current/'
            })
        
        dashboard_data = {
            'user_profile': user_profile,
            'subscription': subscription_info,
            'call_statistics': call_stats,
            'recent_calls': recent_calls_data,
            'billing_info': billing_info,
            'quick_actions': quick_actions,
            'notifications': notifications,
            'summary': {
                'account_status': subscription_info.get('status', 'inactive'),
                'calls_today': CallSession.objects.filter(user=user, started_at__date=today).count(),
                'total_spent': sum(float(bill.amount) for bill in BillingHistory.objects.filter(subscription__user=user, status='paid')) if subscription_info.get('status') != 'inactive' else 0
            }
        }
        
        return Response(dashboard_data, status=status.HTTP_200_OK)


class UserSubscriptionManagementAPIView(APIView):
    """User subscription management"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: "User subscription management data",
            401: "Unauthorized"
        },
        operation_description="Get user subscription management options",
        tags=['Dashboard'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        user = request.user
        
        # Current subscription
        current_subscription = None
        try:
            subscription = user.subscription
            current_subscription = {
                'id': str(subscription.id),
                'plan': {
                    'name': subscription.plan.name,
                    'price': float(subscription.plan.price),
                    'interval': subscription.plan.interval,
                    'features': subscription.plan.features,
                    'call_limit': subscription.plan.call_limit,
                    'agent_limit': subscription.plan.agent_limit
                },
                'status': subscription.status,
                'current_period_start': subscription.current_period_start.isoformat(),
                'current_period_end': subscription.current_period_end.isoformat(),
                'days_remaining': subscription.days_remaining,
                'cancel_at_period_end': subscription.cancel_at_period_end
            }
        except Subscription.DoesNotExist:
            pass
        
        # Available plans
        from subscriptions.models import SubscriptionPlan
        available_plans = SubscriptionPlan.objects.filter(is_active=True)
        plans_data = []
        
        for plan in available_plans:
            is_current = current_subscription and current_subscription['plan']['name'] == plan.name
            plans_data.append({
                'id': str(plan.id),
                'name': plan.name,
                'price': float(plan.price),
                'interval': plan.interval,
                'features': plan.features,
                'call_limit': plan.call_limit,
                'agent_limit': plan.agent_limit,
                'is_current': is_current,
                'is_popular': plan.name.lower() == 'professional',
                'stripe_price_id': plan.stripe_price_id,
                'can_select': not is_current
            })
        
        # Usage for current period
        usage_data = None
        if current_subscription:
            usage = UsageMetrics.objects.filter(
                subscription=user.subscription
            ).order_by('-period_start').first()
            
            if usage:
                usage_data = {
                    'calls_made': usage.calls_made,
                    'call_minutes': usage.call_minutes,
                    'api_requests': usage.api_requests,
                    'storage_used': usage.storage_used,
                    'agents_used': usage.agents_used,
                    'period_start': usage.period_start.isoformat(),
                    'period_end': usage.period_end.isoformat()
                }
        
        return Response({
            'current_subscription': current_subscription,
            'available_plans': plans_data,
            'current_usage': usage_data,
            'can_upgrade': current_subscription is not None,
            'can_cancel': current_subscription and current_subscription['status'] == 'active'
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'action': openapi.Schema(type=openapi.TYPE_STRING, enum=['create', 'upgrade', 'cancel']),
                'plan_id': openapi.Schema(type=openapi.TYPE_STRING, description='Plan ID for create/upgrade')
            },
            required=['action']
        ),
        responses={
            200: "Subscription action completed",
            400: "Bad request"
        },
        operation_description="Perform subscription actions",
        tags=['Dashboard'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        user = request.user
        action = request.data.get('action')
        plan_id = request.data.get('plan_id')
        
        if action == 'create':
            if not plan_id:
                return Response({'error': 'Plan ID required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                from subscriptions.models import SubscriptionPlan
                plan = SubscriptionPlan.objects.get(id=plan_id)
                
                # Create subscription (simplified for demo)
                subscription = Subscription.objects.create(
                    user=user,
                    plan=plan,
                    status='active',
                    current_period_start=timezone.now(),
                    current_period_end=timezone.now() + timedelta(days=30)
                )
                
                return Response({
                    'message': 'Subscription created successfully',
                    'subscription_id': str(subscription.id)
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        elif action == 'cancel':
            try:
                subscription = user.subscription
                subscription.cancel_at_period_end = True
                subscription.save()
                
                return Response({
                    'message': 'Subscription will be cancelled at period end'
                }, status=status.HTTP_200_OK)
                
            except Subscription.DoesNotExist:
                return Response({'error': 'No subscription found'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)


class UserCallHistoryAPIView(APIView):
    """User call history with filters"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status", type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, description="From date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, description="To date (YYYY-MM-DD)", type=openapi.TYPE_STRING)
        ],
        responses={
            200: "User call history",
            401: "Unauthorized"
        },
        operation_description="Get user call history with filtering",
        tags=['Dashboard'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        user = request.user
        
        # Filter parameters
        page = int(request.query_params.get('page', 1))
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Base queryset
        calls = CallSession.objects.filter(user=user).order_by('-started_at')
        
        # Apply filters
        if status_filter:
            calls = calls.filter(status=status_filter)
        if date_from:
            calls = calls.filter(started_at__date__gte=date_from)
        if date_to:
            calls = calls.filter(started_at__date__lte=date_to)
        
        # Pagination
        limit = 20
        offset = (page - 1) * limit
        total_count = calls.count()
        calls = calls[offset:offset + limit]
        
        call_data = []
        for call in calls:
            call_data.append({
                'id': str(call.id),
                'phone_number': call.phone_number,
                'call_type': call.call_type,
                'status': call.status,
                'started_at': call.started_at.isoformat(),
                'ended_at': call.ended_at.isoformat() if call.ended_at else None,
                'duration': call.call_duration_formatted,
                'customer_satisfaction': call.customer_satisfaction,
                'recording_url': call.recording_url,
                'agent': {
                    'name': call.agent.user.get_full_name(),
                    'employee_id': call.agent.employee_id
                } if call.agent else None
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
