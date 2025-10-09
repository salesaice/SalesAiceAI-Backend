from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from subscriptions.models import Subscription, SubscriptionPlan, BillingHistory
from calls.models import CallSession
from accounts.permissions import IsAdmin
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json

User = get_user_model()


class AdminDashboardAPIView(APIView):
    """
    Admin Dashboard API that matches the TypeScript AdminDashboardData interface
    
    Expected TypeScript format:
    {
        metrics: {
            totalUsers: number;
            activeUsers: number;
            totalPackages: number;
            mrrUsd: number;
            callsToday: number;
            churnRatePct: number;
        },
        trends: {
            mrr: SparkPoint[];
            calls: SparkPoint[];
            users: SparkPoint[];
        },
        recentUsers: MiniUser[];
        topPackages: MiniPackage[];
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        tags=['Dashboard'],
        operation_summary="Admin Dashboard Metrics",
        operation_description="Get comprehensive admin dashboard with metrics, trends, users, and packages",
        responses={
            200: "Admin dashboard data retrieved successfully",
            401: "Unauthorized - Authentication required",
            403: "Forbidden - Admin access required"
        }
    )
    def get(self, request):
        try:
            # Date ranges
            today = timezone.now().date()
            this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month = (this_month - timedelta(days=1)).replace(day=1)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            # 1. METRICS
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            total_packages = SubscriptionPlan.objects.count()
            
            # MRR (Monthly Recurring Revenue) in USD
            current_mrr = Subscription.objects.filter(
                status='active'
            ).aggregate(
                mrr=Sum('plan__price')
            )['mrr'] or 0
            
            # Calls today
            calls_today = CallSession.objects.filter(started_at__date=today).count()
            
            # Churn rate calculation (cancelled subscriptions this month vs total active)
            cancelled_this_month = Subscription.objects.filter(
                status='cancelled',
                updated_at__gte=this_month
            ).count()
            total_active = Subscription.objects.filter(status='active').count()
            churn_rate = (cancelled_this_month / max(total_active, 1)) * 100
            
            # 2. TRENDS (last 30 days)
            # Generate trend data points
            trends_data = self.generate_trends(thirty_days_ago, timezone.now())
            
            # 3. RECENT USERS (last 10 users)
            recent_users_queryset = User.objects.select_related().order_by('-date_joined')[:10]
            recent_users = []
            for user in recent_users_queryset:
                recent_users.append({
                    'id': str(user.id),
                    'name': f"{user.first_name} {user.last_name}".strip() or user.email.split('@')[0],
                    'email': user.email,
                    'role': 'admin' if user.is_staff else 'user',
                    'joined_at': user.date_joined.isoformat(),
                    'status': 'active' if user.is_active else 'inactive'
                })
            
            # 4. TOP PACKAGES (by subscriber count)
            top_packages_queryset = SubscriptionPlan.objects.annotate(
                subscriber_count=Count('subscription', filter=Q(subscription__status='active'))
            ).order_by('-subscriber_count')[:5]
            
            top_packages = []
            for plan in top_packages_queryset:
                top_packages.append({
                    'id': str(plan.id),
                    'name': plan.name,  
                    'price_monthly': float(plan.price),
                    'subscribers': plan.subscriber_count,
                    'minutes_included': plan.call_minutes_limit
                })
            
            # Prepare response data
            response_data = {
                'metrics': {
                    'totalUsers': total_users,
                    'activeUsers': active_users,
                    'totalPackages': total_packages,
                    'mrrUsd': float(current_mrr),
                    'callsToday': calls_today,
                    'churnRatePct': round(churn_rate, 2)
                },
                'trends': trends_data,
                'recentUsers': recent_users,
                'topPackages': top_packages
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to load admin dashboard: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def generate_trends(self, start_date, end_date):
        """Generate trend data for the last 30 days"""
        from datetime import date
        
        # Generate date range (last 30 days)
        date_range = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        # MRR trend (daily active subscription revenue)
        mrr_trend = []
        for i, date_point in enumerate(date_range):
            daily_mrr = Subscription.objects.filter(
                status='active',
                created_at__date__lte=date_point
            ).aggregate(mrr=Sum('plan__price'))['mrr'] or 0
            mrr_trend.append({'x': i, 'y': float(daily_mrr)})
        
        # Calls trend (daily call count)
        calls_trend = []
        for i, date_point in enumerate(date_range):
            daily_calls = CallSession.objects.filter(
                started_at__date=date_point
            ).count()
            calls_trend.append({'x': i, 'y': daily_calls})
        
        # Users trend (cumulative user count)
        users_trend = []
        for i, date_point in enumerate(date_range):
            cumulative_users = User.objects.filter(
                date_joined__date__lte=date_point
            ).count()
            users_trend.append({'x': i, 'y': cumulative_users})
        
        return {
            'mrr': mrr_trend,
            'calls': calls_trend,
            'users': users_trend
        }
