from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import User
from .permissions import IsAdmin
from subscriptions.models import Subscription
from calls.models import CallSession


class UserManagementAPIView(APIView):
    """
    User Management API - Complete user data with statistics
    Returns data matching TypeScript User and UsersData interfaces
    """
    permission_classes = [IsAdmin]
    
    @swagger_auto_schema(
        tags=['Admin - User Management'],
        operation_summary="Get All Users with Statistics",
        operation_description="Get comprehensive user data with statistics for admin dashboard",
        responses={
            200: openapi.Response(
                description="Users data with statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'users': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'email': openapi.Schema(type=openapi.TYPE_STRING),
                                    'role': openapi.Schema(type=openapi.TYPE_STRING),
                                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                                    'phone': openapi.Schema(type=openapi.TYPE_STRING),
                                    'company': openapi.Schema(type=openapi.TYPE_STRING),
                                    'joinedAt': openapi.Schema(type=openapi.TYPE_STRING),
                                    'lastLoginAt': openapi.Schema(type=openapi.TYPE_STRING),
                                    'totalCalls': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'minutesUsed': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'currentPlan': openapi.Schema(type=openapi.TYPE_STRING),
                                    'billingStatus': openapi.Schema(type=openapi.TYPE_STRING),
                                    'avatar': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
                        'totalUsers': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'activeUsers': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'bannedUsers': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'stats': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'newUsersThisMonth': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'totalRevenue': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'avgCallsPerUser': openapi.Schema(type=openapi.TYPE_NUMBER),
                            }
                        ),
                    }
                )
            ),
            403: "Forbidden - Admin access required"
        }
    )
    def get(self, request):
        """Get all users with comprehensive statistics"""
        
        # Get all users with related data
        users = User.objects.select_related(
            'subscription'
        ).prefetch_related(
            'calls'
        ).all()
        
        user_data = []
        total_calls = 0
        total_minutes = 0
        
        for user in users:
            # Get user's active subscription
            active_subscription = getattr(user, 'subscription', None)
            current_plan = active_subscription.plan.name if active_subscription and active_subscription.status == 'active' else 'No Plan'
            
            # Get billing status
            billing_status = 'active'
            if active_subscription:
                if active_subscription.status == 'cancelled':
                    billing_status = 'cancelled'
                elif active_subscription.current_period_end and active_subscription.current_period_end < timezone.now():
                    billing_status = 'overdue'
            else:
                billing_status = 'cancelled'
            
            # Get call statistics
            user_calls = user.calls.all()
            user_total_calls = user_calls.count()
            user_minutes_used = sum((call.duration or 0) // 60 for call in user_calls)  # Convert seconds to minutes
            
            total_calls += user_total_calls
            total_minutes += user_minutes_used
            
            # Determine user status
            user_status = 'active' if user.is_active else 'banned'
            
            user_info = {
                'id': str(user.id),
                'name': user.get_full_name() or user.email.split('@')[0],
                'email': user.email,
                'role': user.role,
                'status': user_status,
                'phone': user.phone or None,
                'company': getattr(user, 'company', None),  # Add if company field exists
                'joinedAt': user.date_joined.isoformat(),
                'lastLoginAt': user.last_login.isoformat() if user.last_login else None,
                'totalCalls': user_total_calls,
                'minutesUsed': user_minutes_used,
                'currentPlan': current_plan,
                'billingStatus': billing_status,
                'avatar': user.avatar.url if user.avatar else None,
            }
            user_data.append(user_info)
        
        # Calculate statistics
        total_users = users.count()
        active_users = users.filter(is_active=True).count()
        banned_users = users.filter(is_active=False).count()
        
        # New users this month
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_users_this_month = users.filter(date_joined__gte=current_month_start).count()
        
        # Calculate total revenue (from active subscriptions)
        active_subscriptions = Subscription.objects.filter(status='active').select_related('plan')
        total_revenue = sum(float(sub.plan.price) for sub in active_subscriptions)
        
        # Average calls per user
        avg_calls_per_user = total_calls / total_users if total_users > 0 else 0
        
        response_data = {
            'success': True,
            'users': user_data,
            'totalUsers': total_users,
            'activeUsers': active_users,
            'bannedUsers': banned_users,
            'stats': {
                'newUsersThisMonth': new_users_this_month,
                'totalRevenue': total_revenue,
                'avgCallsPerUser': round(avg_calls_per_user, 2),
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=['Admin - User Management'],
        operation_summary="Update User Status",
        operation_description="Update user status (activate/ban) or role",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['user_id', 'action'],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_STRING, description="User ID"),
                'action': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    enum=['activate', 'ban', 'change_role'],
                    description="Action to perform"
                ),
                'role': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['admin', 'user', 'agent'],
                    description="New role (required if action is change_role)"
                ),
            }
        ),
        responses={
            200: "User updated successfully",
            400: "Bad request",
            404: "User not found",
            403: "Forbidden - Admin access required"
        }
    )
    def post(self, request):
        """Update user status or role"""
        user_id = request.data.get('user_id')
        action = request.data.get('action')
        new_role = request.data.get('role')
        
        if not user_id or not action:
            return Response({
                'success': False,
                'error': 'user_id and action are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
            
            # Prevent self-modification in some cases
            if user == request.user and action == 'ban':
                return Response({
                    'success': False,
                    'error': 'You cannot ban your own account'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if action == 'activate':
                user.is_active = True
                message = f'User {user.email} activated successfully'
                
            elif action == 'ban':
                user.is_active = False
                message = f'User {user.email} banned successfully'
                
            elif action == 'change_role':
                if not new_role or new_role not in ['admin', 'user', 'agent']:
                    return Response({
                        'success': False,
                        'error': 'Valid role is required for change_role action'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                user.role = new_role
                user.is_staff = (new_role == 'admin')
                message = f'User {user.email} role changed to {new_role} successfully'
                
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid action. Use: activate, ban, or change_role'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user.save()
            
            return Response({
                'success': True,
                'message': message,
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'role': user.role,
                    'status': 'active' if user.is_active else 'banned',
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
