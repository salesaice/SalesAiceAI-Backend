"""
Real-time Event Triggers for Agent Management
"""
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime
import json


class AgentEventTrigger:
    """Utility class to trigger real-time events for agent management"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def send_event_to_user(self, user_id, event_type, data):
        """Send real-time event to specific user"""
        if not self.channel_layer:
            return
        
        room_group_name = f"agent_dashboard_{user_id}"
        
        async_to_sync(self.channel_layer.group_send)(
            room_group_name,
            {
                'type': event_type,
                **data,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def agent_status_changed(self, agent, old_status=None):
        """Trigger event when agent status changes"""
        self.send_event_to_user(
            user_id=agent.owner.id,
            event_type='agent_status_changed',
            data={
                'agent_id': str(agent.id),
                'status': agent.status,
                'old_status': old_status,
                'agent_name': agent.name
            }
        )
    
    def campaign_status_changed(self, campaign, old_status=None):
        """Trigger event when campaign status changes"""
        # Send to agent owner
        self.send_event_to_user(
            user_id=campaign.agent.owner.id,
            event_type='campaign_status_changed',
            data={
                'campaign_id': str(campaign.id),
                'agent_id': str(campaign.agent.id),
                'status': campaign.status,
                'old_status': old_status,
                'campaign_name': campaign.name
            }
        )
        
        # Also send to campaign progress room
        if self.channel_layer:
            room_group_name = f"campaign_progress_{campaign.id}"
            async_to_sync(self.channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'campaign_progress_update',
                    'campaign_id': str(campaign.id),
                    'progress': {
                        'status': campaign.status,
                        'total_contacts': campaign.total_contacts,
                        'contacts_called': campaign.contacts_called,
                        'successful_calls': campaign.successful_calls,
                        'conversions': campaign.conversions
                    },
                    'timestamp': datetime.now().isoformat()
                }
            )
    
    def call_queue_updated(self, agent, queue_data=None):
        """Trigger event when call queue is updated"""
        self.send_event_to_user(
            user_id=agent.owner.id,
            event_type='call_queue_updated',
            data={
                'agent_id': str(agent.id),
                'queue_data': queue_data or {},
                'agent_name': agent.name
            }
        )
    
    def dashboard_stats_updated(self, user, stats):
        """Trigger event when dashboard statistics are updated"""
        self.send_event_to_user(
            user_id=user.id,
            event_type='dashboard_stats_updated',
            data={
                'stats': stats
            }
        )
    
    def agent_performance_updated(self, agent, performance_data):
        """Trigger event when agent performance is updated"""
        self.send_event_to_user(
            user_id=agent.owner.id,
            event_type='agent_performance_updated',
            data={
                'agent_id': str(agent.id),
                'performance': performance_data,
                'agent_name': agent.name
            }
        )
    
    def subscription_limit_reached(self, user, limit_type, current_usage, limit_value):
        """Trigger event when subscription limit is reached"""
        self.send_event_to_user(
            user_id=user.id,
            event_type='subscription_limit_reached',
            data={
                'limit_type': limit_type,
                'current_usage': current_usage,
                'limit_value': limit_value,
                'message': f"You have reached your {limit_type} limit of {limit_value}"
            }
        )


# Global instance for easy access
event_trigger = AgentEventTrigger()


def trigger_agent_status_change(agent, old_status=None):
    """Helper function to trigger agent status change event"""
    event_trigger.agent_status_changed(agent, old_status)


def trigger_campaign_status_change(campaign, old_status=None):
    """Helper function to trigger campaign status change event"""
    event_trigger.campaign_status_changed(campaign, old_status)


def trigger_call_queue_update(agent, queue_data=None):
    """Helper function to trigger call queue update event"""
    event_trigger.call_queue_updated(agent, queue_data)


def trigger_dashboard_update(user):
    """Helper function to trigger dashboard update"""
    from .models_new import Agent, Campaign
    from .subscription_utils import get_subscription_summary
    
    # Calculate current stats
    agents = Agent.objects.filter(owner=user)
    total_agents = agents.count()
    active_agents = agents.filter(status='active').count()
    
    total_calls = sum(agent.total_calls for agent in agents)
    total_successful = sum(agent.successful_calls for agent in agents)
    avg_success_rate = round((total_successful / total_calls * 100)) if total_calls > 0 else 0
    
    active_campaigns = Campaign.objects.filter(
        agent__owner=user,
        status='active'
    ).count()
    
    subscription_info = get_subscription_summary(user)
    
    stats = {
        'total_agents': total_agents,
        'active_agents': active_agents,
        'total_calls': total_calls,
        'avg_success_rate': f"{avg_success_rate}%",
        'active_campaigns': active_campaigns,
        'subscription_info': subscription_info
    }
    
    event_trigger.dashboard_stats_updated(user, stats)


def trigger_subscription_limit_warning(user, limit_type, current_usage, limit_value):
    """Helper function to trigger subscription limit warning"""
    event_trigger.subscription_limit_reached(user, limit_type, current_usage, limit_value)