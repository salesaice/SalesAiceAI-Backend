"""
Intelligent Auto Call System with AI Decision Making
==================================================

Enhanced auto-call system where AI agents make all decisions automatically
based on their knowledge, learning data, and intelligent analysis.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .ai_decision_engine import AIAgentDecisionEngine
from .ai_agent_models import AIAgent, CallSession
from .auto_campaign_models import AutoCallCampaign, AutoCampaignContact

logger = logging.getLogger(__name__)


class IntelligentAutoCallSystem:
    """
    Fully automated call system where AI agents make all decisions
    """
    
    def __init__(self, ai_agent: AIAgent):
        self.agent = ai_agent
        self.decision_engine = AIAgentDecisionEngine(ai_agent)
    
    def start_intelligent_campaign(self, campaign: AutoCallCampaign) -> dict:
        """
        AI agent decides when and how to start campaign based on its knowledge
        """
        try:
            # Agent makes intelligent decision about starting campaign
            campaign_decision = self.decision_engine.should_start_calling_campaign(campaign)
            
            if campaign_decision['should_start']:
                # Agent decides to start now
                return self._execute_campaign_start(campaign, campaign_decision)
            else:
                # Agent suggests better timing
                return self._schedule_campaign_intelligently(campaign, campaign_decision)
                
        except Exception as e:
            logger.error(f"Error in intelligent campaign start: {str(e)}")
            return {
                'success': False,
                'message': 'AI decision engine error',
                'error': str(e)
            }
    
    def prioritize_contacts_automatically(self, campaign: AutoCallCampaign) -> dict:
        """
        AI agent automatically prioritizes all contacts based on intelligence
        """
        try:
            contacts = campaign.contacts.filter(status='pending')
            
            # Agent makes intelligent prioritization
            prioritized_contacts = self.decision_engine.prioritize_customers_intelligently(contacts)
            
            return {
                'success': True,
                'message': f'AI agent intelligently prioritized {len(prioritized_contacts)} contacts',
                'prioritization_summary': {
                    'total_contacts': len(prioritized_contacts),
                    'high_priority': len([c for c in prioritized_contacts if c.priority >= 8]),
                    'medium_priority': len([c for c in prioritized_contacts if 5 <= c.priority < 8]),
                    'low_priority': len([c for c in prioritized_contacts if c.priority < 5]),
                }
            }
            
        except Exception as e:
            logger.error(f"Error in automatic prioritization: {str(e)}")
            return {
                'success': False,
                'message': 'AI prioritization failed',
                'error': str(e)
            }
    
    def schedule_calls_intelligently(self, campaign: AutoCallCampaign) -> dict:
        """
        AI agent schedules all calls at optimal times based on learning data
        """
        try:
            contacts = campaign.contacts.filter(status='pending')
            scheduled_count = 0
            
            for contact in contacts:
                # Agent decides optimal schedule for each contact
                schedule_decision = self.decision_engine.decide_call_schedule_intelligently(contact)
                
                if schedule_decision['recommended_datetime']:
                    contact.scheduled_datetime = schedule_decision['recommended_datetime']
                    contact.ai_notes = f"AI Scheduling: {schedule_decision['reasoning']}"
                    contact.save()
                    scheduled_count += 1
            
            return {
                'success': True,
                'message': f'AI agent scheduled {scheduled_count} calls intelligently',
                'scheduling_summary': {
                    'contacts_scheduled': scheduled_count,
                    'ai_confidence': 'high' if scheduled_count > 0 else 'low'
                }
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent scheduling: {str(e)}")
            return {
                'success': False,
                'message': 'AI scheduling failed',
                'error': str(e)
            }
    
    def handle_follow_ups_automatically(self, call_session: CallSession) -> dict:
        """
        AI agent automatically decides and handles follow-ups without human intervention
        """
        try:
            # Agent makes intelligent follow-up decision
            follow_up_decision = self.decision_engine.should_approve_follow_up_automatically(call_session)
            
            if follow_up_decision['auto_approve']:
                return self._create_automatic_follow_up(call_session, follow_up_decision)
            else:
                # Agent decides no follow-up needed or manual review required
                return {
                    'success': True,
                    'action': 'no_follow_up',
                    'message': f"AI agent decided: {follow_up_decision['reasoning']}",
                    'confidence': follow_up_decision['confidence']
                }
                
        except Exception as e:
            logger.error(f"Error in automatic follow-up handling: {str(e)}")
            return {
                'success': False,
                'message': 'AI follow-up decision failed',
                'error': str(e)
            }
    
    def _execute_campaign_start(self, campaign: AutoCallCampaign, decision: dict) -> dict:
        """Execute campaign start based on AI decision"""
        try:
            # Update campaign status
            campaign.status = 'active'
            campaign.started_at = timezone.now()
            campaign.ai_notes = f"AI Decision: {decision['reasoning']}"
            campaign.save()
            
            # Automatically prioritize and schedule
            prioritization_result = self.prioritize_contacts_automatically(campaign)
            scheduling_result = self.schedule_calls_intelligently(campaign)
            
            return {
                'success': True,
                'action': 'campaign_started',
                'message': f"AI agent started campaign with {decision['confidence']*100:.0f}% confidence",
                'ai_reasoning': decision['reasoning'],
                'automation_results': {
                    'prioritization': prioritization_result,
                    'scheduling': scheduling_result
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing campaign start: {str(e)}")
            return {
                'success': False,
                'message': 'Campaign execution failed',
                'error': str(e)
            }
    
    def _schedule_campaign_intelligently(self, campaign: AutoCallCampaign, decision: dict) -> dict:
        """Schedule campaign for optimal time based on AI recommendation"""
        try:
            if decision['recommended_time']:
                # Parse recommended time and schedule
                recommended_hour = int(decision['recommended_time'].split(':')[0])
                
                # Schedule for today if recommended time hasn't passed, else tomorrow
                now = timezone.now()
                if now.hour < recommended_hour:
                    scheduled_start = now.replace(hour=recommended_hour, minute=0, second=0, microsecond=0)
                else:
                    scheduled_start = (now + timedelta(days=1)).replace(hour=recommended_hour, minute=0, second=0, microsecond=0)
                
                campaign.scheduled_start_time = scheduled_start
                campaign.ai_notes = f"AI Recommendation: {decision['reasoning']}"
                campaign.save()
                
                return {
                    'success': True,
                    'action': 'campaign_scheduled',
                    'message': f"AI agent scheduled campaign for {scheduled_start.strftime('%Y-%m-%d %H:%M')}",
                    'ai_reasoning': decision['reasoning'],
                    'confidence': decision['confidence']
                }
            else:
                return {
                    'success': False,
                    'action': 'schedule_failed',
                    'message': "AI agent couldn't determine optimal timing",
                    'ai_reasoning': decision['reasoning']
                }
                
        except Exception as e:
            logger.error(f"Error scheduling campaign: {str(e)}")
            return {
                'success': False,
                'message': 'AI scheduling failed',
                'error': str(e)
            }
    
    def _create_automatic_follow_up(self, call_session: CallSession, decision: dict) -> dict:
        """Create automatic follow-up based on AI decision"""
        try:
            from .ai_agent_models import ScheduledCallback
            
            # Calculate follow-up timing
            timing_map = {
                '24_hours': timedelta(days=1),
                '2_days': timedelta(days=2),
                '3_days': timedelta(days=3),
                '1_week': timedelta(weeks=1)
            }
            
            follow_up_delay = timing_map.get(decision['suggested_timing'], timedelta(days=2))
            scheduled_time = timezone.now() + follow_up_delay
            
            # Create scheduled callback
            callback = ScheduledCallback.objects.create(
                ai_agent=call_session.ai_agent,
                customer_profile=call_session.customer_profile,
                scheduled_datetime=scheduled_time,
                callback_type=decision['suggested_follow_up_type'] or 'general_follow_up',
                notes=f"AI Auto-Follow-up: {decision['reasoning']}",
                status='scheduled'
            )
            
            return {
                'success': True,
                'action': 'follow_up_scheduled',
                'message': f"AI agent scheduled {decision['suggested_follow_up_type']} for {scheduled_time.strftime('%Y-%m-%d %H:%M')}",
                'ai_reasoning': decision['reasoning'],
                'confidence': decision['confidence'],
                'follow_up_id': str(callback.id)
            }
            
        except Exception as e:
            logger.error(f"Error creating automatic follow-up: {str(e)}")
            return {
                'success': False,
                'message': 'Auto follow-up creation failed',
                'error': str(e)
            }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_intelligent_auto_campaign(request):
    """
    API endpoint for starting intelligent auto campaigns
    Agent makes all decisions automatically
    """
    try:
        campaign_id = request.data.get('campaign_id')
        agent_id = request.data.get('agent_id')
        
        if not campaign_id or not agent_id:
            return Response({
                'error': 'campaign_id and agent_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get AI agent and campaign
        ai_agent = AIAgent.objects.get(id=agent_id, client=request.user)
        campaign = AutoCallCampaign.objects.get(id=campaign_id, ai_agent=ai_agent)
        
        # Initialize intelligent system
        intelligent_system = IntelligentAutoCallSystem(ai_agent)
        
        # Agent makes all decisions and starts campaign
        result = intelligent_system.start_intelligent_campaign(campaign)
        
        return Response({
            'success': result['success'],
            'message': result['message'],
            'ai_decision_details': result,
            'agent_info': {
                'name': ai_agent.name,
                'training_level': ai_agent.training_level,
                'conversion_rate': ai_agent.conversion_rate
            }
        })
        
    except AIAgent.DoesNotExist:
        return Response({
            'error': 'AI Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except AutoCallCampaign.DoesNotExist:
        return Response({
            'error': 'Campaign not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in intelligent campaign API: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_automatic_follow_up(request):
    """
    API endpoint for automatic follow-up handling after calls
    """
    try:
        call_session_id = request.data.get('call_session_id')
        
        if not call_session_id:
            return Response({
                'error': 'call_session_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get call session
        call_session = CallSession.objects.get(id=call_session_id, ai_agent__client=request.user)
        
        # Initialize intelligent system
        intelligent_system = IntelligentAutoCallSystem(call_session.ai_agent)
        
        # Agent decides and handles follow-up automatically
        result = intelligent_system.handle_follow_ups_automatically(call_session)
        
        return Response({
            'success': result['success'],
            'action_taken': result.get('action', 'none'),
            'message': result['message'],
            'ai_decision_details': result
        })
        
    except CallSession.DoesNotExist:
        return Response({
            'error': 'Call session not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in automatic follow-up API: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)