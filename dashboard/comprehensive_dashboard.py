from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from accounts.models import User
from accounts.permissions import IsAdmin
from subscriptions.models import Subscription, BillingHistory, UsageRecord, SubscriptionPlan
from calls.models import CallSession, CallQueue

User = get_user_model()


class ComprehensiveDashboardAPIView(APIView):
    """
    Comprehensive Dashboard API matching TypeScript DashboardData interface
    USER ACCESS - Returns structured dashboard data for the authenticated user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Dashboard'],
        operation_summary="User Dashboard Data",
        operation_description="Get comprehensive dashboard data for the authenticated user",
        responses={
            200: openapi.Response(
                description="Dashboard data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'inboundCalls': openapi.Schema(type=openapi.TYPE_INTEGER, description="Total inbound calls this billing cycle"),
                        'outboundCalls': openapi.Schema(type=openapi.TYPE_INTEGER, description="Total outbound calls this billing cycle"),
                        'planName': openapi.Schema(type=openapi.TYPE_STRING, description="Current subscription plan/package"),
                        'planMinutesLimit': openapi.Schema(type=openapi.TYPE_INTEGER, description="Total minutes in current billing cycle"),
                        'planMinutesUsed': openapi.Schema(type=openapi.TYPE_INTEGER, description="Minutes used in current billing cycle"),
                        'renewalDateISO': openapi.Schema(type=openapi.TYPE_STRING, description="Plan renewal/expiry date"),
                        'billingCycleStart': openapi.Schema(type=openapi.TYPE_STRING, description="Start of current billing cycle"),
                        'totalCallsThisCycle': openapi.Schema(type=openapi.TYPE_INTEGER, description="Total calls this billing cycle"),
                        'averageCallDuration': openapi.Schema(type=openapi.TYPE_NUMBER, description="Average call duration in minutes"),
                        'callSuccessRate': openapi.Schema(type=openapi.TYPE_NUMBER, description="Call success rate percentage"),
                        'weeklyCallTrends': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'day': openapi.Schema(type=openapi.TYPE_STRING),
                                    'inbound': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'outbound': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            )
                        ),
                        'hourlyActivity': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'hour': openapi.Schema(type=openapi.TYPE_STRING),
                                    'calls': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            )
                        ),
                        'callTypeDistribution': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'value': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'color': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
                        'monthlyUsage': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'month': openapi.Schema(type=openapi.TYPE_STRING),
                                    'minutes': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'calls': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            )
                        ),
                    }
                )
            ),
            401: "Unauthorized - Authentication required",
            404: "Data not found"
        }
    )
    def get(self, request):
        """Get comprehensive dashboard data for the authenticated user"""
        user = request.user
        
        try:
            # Get user's subscription to determine billing cycle
            user_subscription = Subscription.objects.filter(user=user, status='active').first()
            
            if user_subscription:
                # Use subscription billing cycle
                billing_start = user_subscription.current_period_start.date()
                billing_end = user_subscription.current_period_end.date()
            else:
                # Fallback to current month if no subscription
                today = timezone.now().date()
                billing_start = today.replace(day=1)
                billing_end = today
            
            # Get user's calls for current billing cycle
            current_cycle_calls = CallSession.objects.filter(
                user=user,  # Filter by current user
                started_at__date__gte=billing_start,
                started_at__date__lte=billing_end
            )
            
            inbound_calls = current_cycle_calls.filter(call_type='inbound').count()
            outbound_calls = current_cycle_calls.filter(call_type='outbound').count()
            total_calls = inbound_calls + outbound_calls
            
            # Calculate average call duration and success rate for user
            completed_calls = current_cycle_calls.filter(status='completed')
            avg_duration = completed_calls.aggregate(avg=Avg('duration'))['avg'] or 0
            avg_duration_minutes = round(avg_duration / 60, 2) if avg_duration else 0
            
            success_rate = (completed_calls.count() / total_calls * 100) if total_calls > 0 else 0
            
            # Get user's subscription and plan information
            if user_subscription:
                plan_name = user_subscription.plan.name
                plan_minutes_limit = user_subscription.plan.call_minutes_limit
                plan_minutes_used = user_subscription.minutes_used_this_month
                renewal_date = user_subscription.current_period_end
                billing_cycle_start = user_subscription.current_period_start
            else:
                plan_name = "No Subscription"
                plan_minutes_limit = 0
                plan_minutes_used = 0
                renewal_date = billing_end
                billing_cycle_start = billing_start
            
            # Generate chart data for user
            weekly_trends = self._get_weekly_call_trends_user(user)
            hourly_activity = self._get_hourly_activity_user(user)
            call_distribution = self._get_call_type_distribution_user(user)
            monthly_usage = self._get_monthly_usage_user(user)
            
            dashboard_data = {
                # Summary Stats for User
                'inboundCalls': inbound_calls,
                'outboundCalls': outbound_calls,
                
                # User Subscription Info
                'planName': plan_name,
                'planMinutesLimit': plan_minutes_limit,
                'planMinutesUsed': plan_minutes_used,
                'renewalDateISO': renewal_date.isoformat() if hasattr(renewal_date, 'isoformat') else billing_end.isoformat(),
                'billingCycleStart': billing_cycle_start.isoformat() if hasattr(billing_cycle_start, 'isoformat') else billing_start.isoformat(),
                
                # User metrics
                'totalCallsThisCycle': total_calls,
                'averageCallDuration': avg_duration_minutes,
                'callSuccessRate': round(success_rate, 2),
                
                # Chart Data for User
                'weeklyCallTrends': weekly_trends,
                'hourlyActivity': hourly_activity,
                'callTypeDistribution': call_distribution,
                'monthlyUsage': monthly_usage
            }
            
            return Response(dashboard_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error generating dashboard data: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_weekly_call_trends_user(self, user):
        """Generate weekly call trends for the last 7 days for specific user"""
        trends = []
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)  # Last 7 days
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            day_calls = CallSession.objects.filter(
                user=user,  # Filter by user
                started_at__date=current_date
            )
            
            inbound = day_calls.filter(call_type='inbound').count()
            outbound = day_calls.filter(call_type='outbound').count()
            total = inbound + outbound
            
            trends.append({
                'day': current_date.strftime('%a'),  # Mon, Tue, etc.
                'inbound': inbound,
                'outbound': outbound,
                'total': total
            })
        
        return trends
    
    def _get_hourly_activity_user(self, user):
        """Generate hourly activity for the last 24 hours for specific user"""
        activity = []
        now = timezone.now()
        
        for hour in range(24):
            hour_start = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
            calls = CallSession.objects.filter(
                user=user,  # Filter by user
                started_at__gte=hour_start,
                started_at__lt=hour_end
            ).count()
            
            activity.append({
                'hour': f"{hour:02d}:00",
                'calls': calls
            })
        
        return activity
    
    def _get_call_type_distribution_user(self, user):
        """Generate call type distribution data for specific user"""
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        
        month_calls = CallSession.objects.filter(
            user=user,  # Filter by user
            started_at__date__gte=current_month_start,
            started_at__date__lte=today
        )
        
        inbound_count = month_calls.filter(call_type='inbound').count()
        outbound_count = month_calls.filter(call_type='outbound').count()
        total = inbound_count + outbound_count
        
        if total == 0:
            return []
        
        distribution = [
            {
                'name': 'Inbound Calls (System)',
                'value': inbound_count,
                'color': '#3b82f6'  # Blue
            },
            {
                'name': 'Outbound Calls (System)', 
                'value': outbound_count,
                'color': '#10b981'  # Green
            }
        ]
        
        return distribution
    
    def _get_monthly_usage_user(self, user):
        """Generate monthly usage data for the last 6 months for specific user"""
        usage = []
        current_date = timezone.now().date()
        
        for i in range(6):
            # Calculate month start and end
            if i == 0:
                month_start = current_date.replace(day=1)
                month_end = current_date
            else:
                month_date = current_date.replace(day=1) - timedelta(days=i*30)
                month_start = month_date.replace(day=1)
                # Get last day of month
                if month_start.month == 12:
                    month_end = month_start.replace(year=month_start.year+1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = month_start.replace(month=month_start.month+1, day=1) - timedelta(days=1)
            
            # User's calls for this month
            month_calls = CallSession.objects.filter(
                user=user,  # Filter by user
                started_at__date__gte=month_start,
                started_at__date__lte=month_end
            )
            
            total_calls = month_calls.count()
            total_duration = month_calls.aggregate(total=Sum('duration'))['total'] or 0
            total_minutes = round(total_duration / 60, 2) if total_duration else 0
            
            usage.append({
                'month': month_start.strftime('%b %Y'),  # Jan 2024
                'minutes': total_minutes,
                'calls': total_calls
            })
        
        return list(reversed(usage))  # Oldest first
