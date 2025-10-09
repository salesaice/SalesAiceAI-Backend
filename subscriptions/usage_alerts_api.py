from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timedelta

from .models import Subscription, UsageAlert, UsageRecord


class UserUsageAlertsAPIView(APIView):
    """
    User Usage Alerts - Monitor usage and send alerts when limits are near/exceeded
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Usage Management'],
        operation_summary="Get Usage Alerts",
        operation_description="Get user's usage alerts and current usage status",
        responses={
            200: openapi.Response(
                description="Usage alerts and status",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'current_usage': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'minutes_used': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'minutes_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'usage_percentage': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'days_remaining': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'status': openapi.Schema(type=openapi.TYPE_STRING, enum=['normal', 'warning', 'critical', 'exceeded']),
                            }
                        ),
                        'alerts': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'alert_type': openapi.Schema(type=openapi.TYPE_STRING),
                                    'threshold_percentage': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                                    'is_triggered': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'triggered_at': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        )
                    }
                )
            ),
            404: "No active subscription found",
            401: "Authentication required"
        }
    )
    def get(self, request):
        """Get user's usage alerts and current status"""
        user = request.user
        
        try:
            subscription = Subscription.objects.select_related('plan').get(
                user=user,
                status='active'
            )
            
            # Calculate current usage
            minutes_used = subscription.minutes_used_this_month
            minutes_limit = subscription.plan.call_minutes_limit
            usage_percentage = (minutes_used / minutes_limit * 100) if minutes_limit > 0 else 0
            
            # Calculate days remaining in current period
            days_remaining = 0
            if subscription.current_period_end:
                days_remaining = (subscription.current_period_end.date() - timezone.now().date()).days
            
            # Determine usage status
            if usage_percentage >= 100:
                usage_status = 'exceeded'
            elif usage_percentage >= 90:
                usage_status = 'critical'
            elif usage_percentage >= 75:
                usage_status = 'warning'
            else:
                usage_status = 'normal'
            
            current_usage = {
                'minutes_used': minutes_used,
                'minutes_limit': minutes_limit,
                'usage_percentage': round(usage_percentage, 2),
                'days_remaining': max(0, days_remaining),
                'status': usage_status,
                'plan_name': subscription.plan.name,
                'billing_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None
            }
            
            # Get usage alerts
            usage_alerts = UsageAlert.objects.filter(
                subscription=subscription
            ).order_by('-created_at')
            
            alerts = []
            for alert in usage_alerts:
                alerts.append({
                    'id': str(alert.id),
                    'alert_type': alert.alert_type,
                    'threshold_percentage': alert.threshold_percentage,
                    'message': alert.message,
                    'is_triggered': alert.is_triggered,
                    'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None,
                    'created_at': alert.created_at.isoformat(),
                })
            
            # Create default alerts if none exist
            if not usage_alerts.exists():
                self._create_default_alerts(subscription)
                
                # Re-fetch alerts after creation
                usage_alerts = UsageAlert.objects.filter(subscription=subscription)
                alerts = []
                for alert in usage_alerts:
                    alerts.append({
                        'id': str(alert.id),
                        'alert_type': alert.alert_type,
                        'threshold_percentage': alert.threshold_percentage,
                        'message': alert.message,
                        'is_triggered': alert.is_triggered,
                        'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None,
                        'created_at': alert.created_at.isoformat(),
                    })
            
            # Check and trigger alerts based on current usage
            self._check_and_trigger_alerts(subscription, usage_percentage)
            
            return Response({
                'success': True,
                'current_usage': current_usage,
                'alerts': alerts,
                'recommendations': self._get_usage_recommendations(usage_status, usage_percentage, subscription)
            }, status=status.HTTP_200_OK)
            
        except Subscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active subscription found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _create_default_alerts(self, subscription):
        """Create default usage alerts for a subscription"""
        default_alerts = [
            {
                'alert_type': 'usage_warning',
                'threshold_percentage': 75,
                'message': f'You have used 75% of your {subscription.plan.name} plan minutes.'
            },
            {
                'alert_type': 'usage_critical',
                'threshold_percentage': 90,
                'message': f'You have used 90% of your {subscription.plan.name} plan minutes.'
            },
            {
                'alert_type': 'usage_exceeded',
                'threshold_percentage': 100,
                'message': f'You have exceeded your {subscription.plan.name} plan minutes limit.'
            }
        ]
        
        for alert_data in default_alerts:
            UsageAlert.objects.create(
                subscription=subscription,
                alert_type=alert_data['alert_type'],
                threshold_percentage=alert_data['threshold_percentage'],
                message=alert_data['message']
            )
    
    def _check_and_trigger_alerts(self, subscription, usage_percentage):
        """Check and trigger alerts based on current usage"""
        alerts = UsageAlert.objects.filter(
            subscription=subscription,
            threshold_percentage__lte=usage_percentage,
            is_triggered=False
        )
        
        for alert in alerts:
            alert.is_triggered = True
            alert.triggered_at = timezone.now()
            alert.save()
    
    def _get_usage_recommendations(self, usage_status, usage_percentage, subscription):
        """Get usage recommendations based on current status"""
        recommendations = []
        
        if usage_status == 'exceeded':
            recommendations.extend([
                {
                    'type': 'upgrade',
                    'title': 'Upgrade Your Plan',
                    'message': 'Consider upgrading to a higher plan to avoid overage charges.',
                    'action': 'upgrade',
                    'priority': 'high'
                },
                {
                    'type': 'usage',
                    'title': 'Monitor Call Usage',
                    'message': 'Track your call usage more closely to stay within limits.',
                    'priority': 'medium'
                }
            ])
        elif usage_status == 'critical':
            recommendations.extend([
                {
                    'type': 'warning',
                    'title': 'Approaching Limit',
                    'message': f'You have used {usage_percentage:.1f}% of your plan. Consider upgrading.',
                    'priority': 'high'
                },
                {
                    'type': 'upgrade',
                    'title': 'Upgrade Available',
                    'message': 'Upgrade to avoid service interruption.',
                    'action': 'upgrade',
                    'priority': 'medium'
                }
            ])
        elif usage_status == 'warning':
            recommendations.append({
                'type': 'info',
                'title': 'Usage Alert',
                'message': f'You have used {usage_percentage:.1f}% of your plan.',
                'priority': 'low'
            })
        
        return recommendations


class PlanFeatureAccessAPIView(APIView):
    """
    Plan Feature Access - Check if user has access to specific features based on their plan
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Feature Access'],
        operation_summary="Check Feature Access",
        operation_description="Check if user has access to specific features based on their plan",
        manual_parameters=[
            openapi.Parameter('feature', openapi.IN_QUERY, description="Feature to check", type=openapi.TYPE_STRING, 
                            enum=['analytics', 'advanced_analytics', 'api_access', 'call_recording', 'call_transcription', 
                                  'sentiment_analysis', 'auto_campaigns', 'crm_integration', 'priority_support'])
        ],
        responses={
            200: openapi.Response(
                description="Feature access information",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'feature_access': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'analytics': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'advanced_analytics': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'api_access': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'call_recording': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'call_transcription': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'sentiment_analysis': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'auto_campaigns': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'crm_integration': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'priority_support': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            }
                        ),
                        'plan_limits': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'agents_allowed': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'ai_agents_allowed': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'concurrent_calls': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'storage_gb': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'call_minutes_limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        )
                    }
                )
            ),
            404: "No active subscription found",
            401: "Authentication required"
        }
    )
    def get(self, request):
        """Get user's feature access based on their plan"""
        user = request.user
        feature_query = request.query_params.get('feature')
        
        try:
            subscription = Subscription.objects.select_related('plan').get(
                user=user,
                status='active'
            )
            
            plan = subscription.plan
            
            # Map all feature access
            feature_access = {
                'analytics': plan.analytics_access,
                'advanced_analytics': plan.advanced_analytics,
                'api_access': plan.api_access,
                'webhook_access': plan.webhook_access,
                'call_recording': plan.call_recording,
                'call_transcription': plan.call_transcription,
                'sentiment_analysis': plan.sentiment_analysis,
                'auto_campaigns': plan.auto_campaigns,
                'crm_integration': plan.crm_integration,
                'priority_support': plan.priority_support,
                'custom_integration': plan.custom_integration,
            }
            
            # Plan limits
            plan_limits = {
                'agents_allowed': plan.agents_allowed,
                'ai_agents_allowed': plan.ai_agents_allowed,
                'concurrent_calls': plan.concurrent_calls,
                'storage_gb': plan.storage_gb,
                'call_minutes_limit': plan.call_minutes_limit,
                'backup_retention_days': plan.backup_retention_days,
            }
            
            # If specific feature requested, return detailed info
            if feature_query:
                if feature_query in feature_access:
                    has_access = feature_access[feature_query]
                    return Response({
                        'success': True,
                        'feature': feature_query,
                        'has_access': has_access,
                        'plan_name': plan.name,
                        'message': f'Access {"granted" if has_access else "denied"} for {feature_query}',
                        'upgrade_required': not has_access
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'error': f'Unknown feature: {feature_query}',
                        'available_features': list(feature_access.keys())
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Return all feature access
            return Response({
                'success': True,
                'plan_name': plan.name,
                'plan_type': plan.plan_type,
                'feature_access': feature_access,
                'plan_limits': plan_limits,
                'usage_status': {
                    'minutes_used': subscription.minutes_used_this_month,
                    'minutes_remaining': max(0, plan.call_minutes_limit - subscription.minutes_used_this_month),
                    'usage_percentage': (subscription.minutes_used_this_month / plan.call_minutes_limit * 100) if plan.call_minutes_limit > 0 else 0
                }
            }, status=status.HTTP_200_OK)
            
        except Subscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active subscription found',
                'message': 'Please subscribe to a plan to access features'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @swagger_auto_schema(
        tags=['User - Feature Access'],
        operation_summary="Validate Feature Access",
        operation_description="Validate if user can perform a specific action based on their plan",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['feature', 'action'],
            properties={
                'feature': openapi.Schema(type=openapi.TYPE_STRING, description="Feature to validate"),
                'action': openapi.Schema(type=openapi.TYPE_STRING, description="Action to perform"),
                'resource_count': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of resources (for limit checking)"),
            }
        ),
        responses={
            200: "Feature access validated",
            403: "Feature access denied",
            401: "Authentication required"
        }
    )
    def post(self, request):
        """Validate if user can perform a specific action"""
        user = request.user
        data = request.data
        feature = data.get('feature')
        action = data.get('action')
        resource_count = data.get('resource_count', 1)
        
        try:
            subscription = Subscription.objects.select_related('plan').get(
                user=user,
                status='active'
            )
            
            plan = subscription.plan
            
            # Validate feature access
            validation_result = self._validate_feature_access(plan, feature, action, resource_count)
            
            if validation_result['allowed']:
                return Response({
                    'success': True,
                    'access_granted': True,
                    'message': validation_result['message'],
                    'feature': feature,
                    'action': action
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'access_granted': False,
                    'message': validation_result['message'],
                    'feature': feature,
                    'action': action,
                    'upgrade_required': validation_result.get('upgrade_required', False),
                    'current_limit': validation_result.get('current_limit'),
                    'requested': resource_count
                }, status=status.HTTP_403_FORBIDDEN)
                
        except Subscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active subscription found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _validate_feature_access(self, plan, feature, action, resource_count):
        """Validate specific feature access and limits"""
        
        # Feature access validation
        feature_map = {
            'analytics': plan.analytics_access,
            'advanced_analytics': plan.advanced_analytics,
            'api_access': plan.api_access,
            'call_recording': plan.call_recording,
            'call_transcription': plan.call_transcription,
            'sentiment_analysis': plan.sentiment_analysis,
            'auto_campaigns': plan.auto_campaigns,
            'crm_integration': plan.crm_integration,
            'priority_support': plan.priority_support,
        }
        
        # Resource limit validation
        limit_map = {
            'agents': plan.agents_allowed,
            'ai_agents': plan.ai_agents_allowed,
            'concurrent_calls': plan.concurrent_calls,
            'storage_gb': plan.storage_gb,
        }
        
        # Check feature access
        if feature in feature_map:
            if not feature_map[feature]:
                return {
                    'allowed': False,
                    'message': f'{feature} is not available in your {plan.name} plan',
                    'upgrade_required': True
                }
        
        # Check resource limits
        if feature in limit_map:
            current_limit = limit_map[feature]
            if resource_count > current_limit:
                return {
                    'allowed': False,
                    'message': f'Requested {resource_count} {feature} exceeds your plan limit of {current_limit}',
                    'current_limit': current_limit,
                    'upgrade_required': True
                }
        
        # Check usage limits (for calls/minutes)
        if feature == 'call_minutes':
            # This would need to check current usage against limits
            pass
        
        return {
            'allowed': True,
            'message': f'Access granted for {feature}'
        }
