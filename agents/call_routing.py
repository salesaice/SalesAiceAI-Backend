"""
Intelligent Inbound Call Routing System
This module handles smart routing of incoming calls to appropriate agents.
"""

from django.db import models
from django.utils import timezone
from .models import Agent
from .ai_agent_models import CallSession
import logging
import random

logger = logging.getLogger(__name__)


class CallRoutingManager:
    """Manages intelligent routing of inbound calls to appropriate agents"""
    
    @staticmethod
    def get_available_inbound_agents():
        """Get all available inbound agents"""
        return Agent.objects.filter(
            agent_type='inbound',
            status='active',
            auto_answer_enabled=True
        ).order_by('calls_handled', 'id')
    
    @staticmethod
    def route_call_round_robin():
        """Route call using round-robin distribution (least busy agent first)"""
        agents = CallRoutingManager.get_available_inbound_agents()
        
        if not agents.exists():
            logger.warning("No available inbound agents for call routing")
            return None
            
        # Get agent with least calls handled
        selected_agent = agents.first()
        logger.info(f"Round-robin routing selected agent: {selected_agent.name} (ID: {selected_agent.id})")
        
        return selected_agent
    
    @staticmethod
    def route_call_by_priority():
        """Route call by agent priority (if priority field exists)"""
        agents = CallRoutingManager.get_available_inbound_agents()
        
        if not agents.exists():
            return None
            
        # If agents have priority field, order by priority then by calls handled
        if hasattr(Agent, 'priority'):
            selected_agent = agents.order_by('priority', 'calls_handled').first()
        else:
            # Fallback to round-robin
            selected_agent = agents.first()
            
        logger.info(f"Priority routing selected agent: {selected_agent.name}")
        return selected_agent
    
    @staticmethod
    def route_call_by_specialization(call_context="general"):
        """Route call based on agent specialization"""
        agents = CallRoutingManager.get_available_inbound_agents()
        
        if not agents.exists():
            return None
        
        # Check if agents have specialization field
        if hasattr(Agent, 'specialization'):
            # Try to match specialization
            specialized_agents = agents.filter(specialization=call_context)
            if specialized_agents.exists():
                selected_agent = specialized_agents.order_by('calls_handled').first()
                logger.info(f"Specialization routing ({call_context}) selected: {selected_agent.name}")
                return selected_agent
        
        # Fallback to round-robin if no specialization match
        return CallRoutingManager.route_call_round_robin()
    
    @staticmethod
    def analyze_caller_intent(caller_number=None, call_history=None):
        """Analyze caller intent for smart routing"""
        
        # Default context
        context = "general"
        
        # Check if this caller has previous call history
        if caller_number:
            previous_calls = CallSession.objects.filter(
                phone_number=caller_number
            ).order_by('-initiated_at')[:3]  # Last 3 calls
            
            if previous_calls.exists():
                # Analyze previous call outcomes
                successful_calls = previous_calls.filter(outcome='successful')
                if successful_calls.exists():
                    # If previous calls were successful with specific agent type
                    last_successful = successful_calls.first()
                    if hasattr(last_successful, 'ai_agent') and last_successful.ai_agent:
                        if hasattr(last_successful.ai_agent, 'specialization'):
                            context = last_successful.ai_agent.specialization
                            logger.info(f"Routing based on previous successful call: {context}")
        
        return context
    
    @staticmethod
    def route_incoming_call(caller_number=None, twilio_data=None):
        """Main routing function for incoming calls"""
        
        try:
            logger.info(f"Routing incoming call from: {caller_number}")
            
            # Step 1: Analyze caller context
            caller_context = CallRoutingManager.analyze_caller_intent(caller_number)
            
            # Step 2: Try specialized routing first
            selected_agent = CallRoutingManager.route_call_by_specialization(caller_context)
            
            # Step 3: Fallback to round-robin if no specialized agent
            if not selected_agent:
                selected_agent = CallRoutingManager.route_call_round_robin()
            
            # Step 4: Final fallback - get any active inbound agent
            if not selected_agent:
                all_inbound = Agent.objects.filter(agent_type='inbound', status='active')
                if all_inbound.exists():
                    selected_agent = all_inbound.first()
                    logger.warning(f"Using fallback agent (auto_answer disabled): {selected_agent.name}")
            
            if selected_agent:
                # Update agent's call count for round-robin
                selected_agent.calls_handled += 1
                selected_agent.total_calls += 1
                selected_agent.save(update_fields=['calls_handled', 'total_calls'])
                
                logger.info(f"✅ Call routed to agent: {selected_agent.name} (Total calls: {selected_agent.calls_handled})")
                
                return {
                    'agent': selected_agent,
                    'routing_method': 'intelligent',
                    'context': caller_context,
                    'success': True
                }
            else:
                logger.error("❌ No available agents for inbound call routing")
                return {
                    'agent': None,
                    'routing_method': 'failed',
                    'context': caller_context,
                    'success': False,
                    'error': 'No available inbound agents'
                }
                
        except Exception as e:
            logger.error(f"Error in call routing: {str(e)}")
            return {
                'agent': None,
                'routing_method': 'error',
                'context': 'unknown',
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_routing_stats():
        """Get call routing statistics"""
        total_inbound_agents = Agent.objects.filter(agent_type='inbound').count()
        active_inbound_agents = Agent.objects.filter(
            agent_type='inbound', 
            status='active'
        ).count()
        auto_answer_agents = Agent.objects.filter(
            agent_type='inbound',
            status='active', 
            auto_answer_enabled=True
        ).count()
        
        return {
            'total_inbound_agents': total_inbound_agents,
            'active_inbound_agents': active_inbound_agents,
            'auto_answer_agents': auto_answer_agents,
            'routing_ready': auto_answer_agents > 0
        }


class CallRoutingHistory(models.Model):
    """Track call routing decisions for analytics"""
    
    caller_number = models.CharField(max_length=20)
    selected_agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True)
    routing_method = models.CharField(max_length=50)
    routing_context = models.CharField(max_length=100, default='general')
    routed_at = models.DateTimeField(auto_now_add=True)
    call_successful = models.BooleanField(null=True, blank=True)
    
    class Meta:
        ordering = ['-routed_at']
        verbose_name = "Call Routing Record"
        verbose_name_plural = "Call Routing Records"
    
    def __str__(self):
        return f"Call from {self.caller_number} → {self.selected_agent.name if self.selected_agent else 'No Agent'}"