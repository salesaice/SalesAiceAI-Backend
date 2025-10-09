from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import SubscriptionPlan, Subscription


class UserPlansComparisonAPIView(APIView):
    """
    Simple Plans Comparison API - Returns all plans with current plan highlighted
    Exactly matches your TypeScript interface
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User - Plans Comparison'],
        operation_summary="Get Plans with Current Plan Highlighted",
        operation_description="Get all available plans with current user's plan highlighted",
        responses={
            200: openapi.Response(
                description="Plans comparison data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'plans': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'features': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(type=openapi.TYPE_STRING)
                                    ),
                                    'isCurrentPlan': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'type': openapi.Schema(type=openapi.TYPE_STRING, enum=['downgrade', 'current', 'upgrade']),
                                    'popular': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                                }
                            )
                        )
                    }
                )
            ),
            401: "Authentication required"
        }
    )
    def get(self, request):
        """Get all plans with current plan highlighted"""
        user = request.user
        
        try:
            # Get user's current subscription
            current_subscription = None
            try:
                current_subscription = Subscription.objects.select_related('plan').get(
                    user=user,
                    status__in=['active', 'trialing', 'past_due', 'pending']
                )
            except Subscription.DoesNotExist:
                pass
            
            # Get all active plans
            all_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
            
            plans_data = []
            
            for plan in all_plans:
                # Build features list - exactly as requested
                features = []
                
                if plan.call_minutes_limit:
                    features.append(f"Up to {plan.call_minutes_limit:,} minutes/month")
                
                if plan.agents_allowed:
                    if plan.agents_allowed > 1:
                        features.append(f"Up to {plan.agents_allowed} agents")
                    else:
                        features.append(f"{plan.agents_allowed} agent")
                
                # Add advanced features based on plan capabilities or price
                if hasattr(plan, 'advanced_analytics') and plan.advanced_analytics:
                    features.append("Advanced AI agents")
                elif plan.price >= 50:  # Higher tier plans
                    features.append("Advanced AI agents")
                
                if hasattr(plan, 'analytics_access') and plan.analytics_access:
                    features.append("Real-time analytics")
                elif plan.price >= 25:  # Mid-tier and above
                    features.append("Real-time analytics")
                
                if hasattr(plan, 'priority_support') and plan.priority_support:
                    features.append("Priority support")
                elif plan.price >= 75:  # Premium plans
                    features.append("Priority support")
                
                if hasattr(plan, 'custom_integration') and plan.custom_integration:
                    features.append("Custom integrations")
                elif plan.price >= 100:  # Enterprise plans
                    features.append("Custom integrations")
                
                # Determine if this is current plan and type
                is_current = current_subscription and current_subscription.plan.id == plan.id
                
                if is_current:
                    plan_type = 'current'
                elif current_subscription:
                    # User has a subscription but this is not their current plan
                    if current_subscription.plan.price < plan.price:
                        plan_type = 'upgrade'
                    else:
                        plan_type = 'downgrade'
                else:
                    # User has no subscription, all plans are upgrades
                    plan_type = 'upgrade'
                
                # Build plan data exactly as your TypeScript interface
                plan_data = {
                    'id': str(plan.id),
                    'name': plan.name,
                    'price': float(plan.price),
                    'features': features,
                    'isCurrentPlan': is_current,
                    'type': plan_type,
                    'popular': getattr(plan, 'is_popular', False)
                }
                
                plans_data.append(plan_data)
            
            return Response({
                'success': True,
                'plans': plans_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error fetching plans: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
