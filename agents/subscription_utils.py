"""
Subscription and Package Limits Utility Functions for Agents
"""
from datetime import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class SubscriptionLimitError(Exception):
    """Custom exception for subscription limit violations"""
    pass


def check_subscription_status(user):
    """Check if user has active subscription"""
    try:
        from subscriptions.models import Subscription
        
        active_subscription = Subscription.objects.filter(
            user=user,
            status='active',
            end_date__gte=timezone.now().date()
        ).first()
        
        return {
            'has_active_subscription': bool(active_subscription),
            'subscription': active_subscription,
            'plan': active_subscription.plan if active_subscription else None
        }
    except ImportError:
        # If subscription models not available, return basic info
        return {
            'has_active_subscription': True,  # Allow for development
            'subscription': None,
            'plan': None
        }


def get_agent_limits(user):
    """Get agent limits for user's subscription plan"""
    subscription_info = check_subscription_status(user)
    
    if not subscription_info['has_active_subscription']:
        return {
            'agents_allowed': 0,
            'ai_agents_allowed': 0,
            'can_create_agents': False,
            'limit_message': "No active subscription. Please upgrade your plan."
        }
    
    plan = subscription_info['plan']
    if not plan:
        # Default limits for development/testing
        return {
            'agents_allowed': 3,
            'ai_agents_allowed': 2,
            'can_create_agents': True,
            'limit_message': "Development mode - default limits applied"
        }
    
    # Get limits from subscription plan
    agents_allowed = getattr(plan, 'agents_allowed', 1)
    ai_agents_allowed = getattr(plan, 'ai_agents_allowed', agents_allowed)
    
    return {
        'agents_allowed': agents_allowed,
        'ai_agents_allowed': ai_agents_allowed,
        'can_create_agents': True,
        'limit_message': f"Your plan allows {agents_allowed} agents"
    }


def get_current_agent_usage(user):
    """Get current agent usage for user"""
    from .models_new import Agent
    
    total_agents = Agent.objects.filter(owner=user).count()
    active_agents = Agent.objects.filter(owner=user, status='active').count()
    ai_agents = Agent.objects.filter(owner=user, human_operator__isnull=True).count()
    
    return {
        'total_agents': total_agents,
        'active_agents': active_agents,
        'ai_agents': ai_agents,
        'inbound_agents': Agent.objects.filter(owner=user, agent_type='inbound').count(),
        'outbound_agents': Agent.objects.filter(owner=user, agent_type='outbound').count()
    }


def can_create_agent(user, agent_type='inbound'):
    """Check if user can create a new agent"""
    limits = get_agent_limits(user)
    usage = get_current_agent_usage(user)
    
    if not limits['can_create_agents']:
        return {
            'can_create': False,
            'reason': limits['limit_message'],
            'current_usage': usage,
            'limits': limits
        }
    
    # Check total agent limit
    if usage['total_agents'] >= limits['agents_allowed']:
        return {
            'can_create': False,
            'reason': f"You have reached your agent limit of {limits['agents_allowed']} agents. Please upgrade your plan.",
            'current_usage': usage,
            'limits': limits
        }
    
    # Check AI agent limit (assuming most agents are AI agents)
    if usage['ai_agents'] >= limits['ai_agents_allowed']:
        return {
            'can_create': False,
            'reason': f"You have reached your AI agent limit of {limits['ai_agents_allowed']} AI agents. Please upgrade your plan.",
            'current_usage': usage,
            'limits': limits
        }
    
    return {
        'can_create': True,
        'reason': "Agent creation allowed",
        'current_usage': usage,
        'limits': limits
    }


def validate_agent_creation(user, agent_type='inbound'):
    """Validate if agent creation is allowed and raise exception if not"""
    result = can_create_agent(user, agent_type)
    
    if not result['can_create']:
        raise SubscriptionLimitError(result['reason'])
    
    return result


def get_subscription_summary(user):
    """Get comprehensive subscription and usage summary"""
    subscription_info = check_subscription_status(user)
    limits = get_agent_limits(user)
    usage = get_current_agent_usage(user)
    creation_status = can_create_agent(user)
    
    return {
        'subscription_status': subscription_info,
        'limits': limits,
        'current_usage': usage,
        'can_create_more': creation_status['can_create'],
        'remaining_agents': max(0, limits['agents_allowed'] - usage['total_agents']),
        'usage_percentage': round((usage['total_agents'] / limits['agents_allowed']) * 100, 1) if limits['agents_allowed'] > 0 else 0
    }


def enforce_agent_limits_decorator(view_func):
    """Decorator to enforce agent limits on views"""
    def wrapper(request, *args, **kwargs):
        if request.method in ['POST'] and 'create' in request.path.lower():
            try:
                validate_agent_creation(request.user)
            except SubscriptionLimitError as e:
                from rest_framework.response import Response
                from rest_framework import status
                
                return Response({
                    'success': False,
                    'error': str(e),
                    'subscription_info': get_subscription_summary(request.user)
                }, status=status.HTTP_403_FORBIDDEN)
        
        return view_func(request, *args, **kwargs)
    return wrapper