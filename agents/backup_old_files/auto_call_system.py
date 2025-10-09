from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
import logging
import json

from .ai_agent_models import AIAgent, CustomerProfile, CallSession
from .auto_campaign_models import AutoCallCampaign, AutoCampaignContact
from .twilio_service import TwilioCallService
from .homeai_integration import HomeAIService

logger = logging.getLogger(__name__)


class AutoCallCampaignAPIView(APIView):
    """
    Automatic Call Campaign Management
    System khud se calls start karta hai
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Start automatic call campaign"""
        try:
            agent = request.user.ai_agent
            data = request.data
            
            campaign_type = data.get('campaign_type', 'general')  # general, followup, new_leads
            customer_filters = data.get('customer_filters', {})
            call_schedule = data.get('call_schedule', {})
            
            # Create campaign
            campaign = AutoCallCampaign.objects.create(
                ai_agent=agent,
                name=data.get('campaign_name', f'Auto Campaign {datetime.now().strftime("%m/%d %H:%M")}'),
                campaign_type=campaign_type,
                status='active',
                target_customers=data.get('target_count', 50),
                calls_per_hour=data.get('calls_per_hour', 10),
                working_hours_start=call_schedule.get('start_time', '09:00'),
                working_hours_end=call_schedule.get('end_time', '17:00'),
                campaign_data={
                    'auto_start': True,
                    'customer_filters': customer_filters,
                    'call_script': data.get('call_script', agent.sales_script),
                    'max_attempts_per_customer': data.get('max_attempts', 3),
                    'time_between_attempts': data.get('retry_delay_hours', 24)
                }
            )
            
            # Get customers based on filters
            customers = self._get_filtered_customers(agent, customer_filters)
            
            # Add customers to campaign
            campaign_contacts = []
            for customer in customers:
                campaign_contacts.append(AutoCampaignContact(
                    campaign=campaign,
                    customer_profile=customer,
                    status='pending',
                    priority=self._calculate_customer_priority(customer),
                    scheduled_datetime=timezone.now()
                ))
            
            AutoCampaignContact.objects.bulk_create(campaign_contacts)
            
            # Start immediate calls if requested
            if data.get('start_immediately', False):
                self._start_immediate_calls(campaign, data.get('immediate_call_count', 5))
            
            return Response({
                'message': 'Auto call campaign created successfully',
                'campaign_id': str(campaign.id),
                'campaign_name': campaign.name,
                'total_customers': len(campaign_contacts),
                'status': campaign.status,
                'calls_per_hour': campaign.calls_per_hour,
                'next_actions': [
                    'Campaign is now active',
                    'Calls will start automatically based on schedule',
                    'Monitor progress in dashboard',
                    'Adjust settings anytime'
                ]
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Auto campaign creation error: {str(e)}")
            return Response({
                'error': f'Failed to create campaign: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        """Get active campaigns and their status"""
        try:
            agent = request.user.ai_agent
            campaigns = agent.auto_campaigns.filter(status__in=['active', 'paused']).order_by('-created_at')
            
            campaign_data = []
            for campaign in campaigns:
                contacts = campaign.contacts.all()
                campaign_data.append({
                    'id': str(campaign.id),
                    'name': campaign.name,
                    'status': campaign.status,
                    'campaign_type': campaign.campaign_type,
                    'total_customers': contacts.count(),
                    'calls_completed': contacts.filter(status='completed').count(),
                    'calls_pending': contacts.filter(status='pending').count(),
                    'calls_in_progress': contacts.filter(status='calling').count(),
                    'success_rate': self._calculate_success_rate(contacts),
                    'calls_per_hour': campaign.calls_per_hour,
                    'created_at': campaign.created_at.isoformat(),
                    'next_call_time': self._get_next_call_time(campaign)
                })
            
            return Response({
                'active_campaigns': campaign_data,
                'total_active': len(campaign_data),
                'agent_status': agent.status
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to get campaigns: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Update campaign settings"""
        try:
            agent = request.user.ai_agent
            data = request.data
            campaign_id = data.get('campaign_id')
            
            campaign = AutoCallCampaign.objects.get(id=campaign_id, ai_agent=agent)
            
            # Update campaign settings
            if 'status' in data:
                campaign.status = data['status']  # active, paused, stopped
            
            if 'calls_per_hour' in data:
                campaign.calls_per_hour = data['calls_per_hour']
            
            if 'working_hours' in data:
                campaign.working_hours_start = data['working_hours'].get('start', campaign.working_hours_start)
                campaign.working_hours_end = data['working_hours'].get('end', campaign.working_hours_end)
            
            campaign.save()
            
            return Response({
                'message': 'Campaign updated successfully',
                'campaign_id': str(campaign.id),
                'new_status': campaign.status,
                'calls_per_hour': campaign.calls_per_hour
            }, status=status.HTTP_200_OK)
            
        except AutoCallCampaign.DoesNotExist:
            return Response({'error': 'Campaign not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def _get_filtered_customers(self, agent, filters):
        """Get customers based on filters"""
        customers = agent.customer_profiles.filter(is_do_not_call=False)
        
        # Filter by interest level
        if filters.get('interest_levels'):
            customers = customers.filter(interest_level__in=filters['interest_levels'])
        
        # Filter by last call date
        if filters.get('days_since_last_call'):
            days_ago = timezone.now() - timedelta(days=filters['days_since_last_call'])
            customers = customers.filter(
                models.Q(last_interaction__lt=days_ago) | models.Q(last_interaction__isnull=True)
            )
        
        # Filter by call success
        if filters.get('only_unconverted'):
            customers = customers.filter(is_converted=False)
        
        # Limit results
        limit = filters.get('max_customers', 100)
        return customers[:limit]
    
    def _calculate_customer_priority(self, customer):
        """Calculate customer priority for calling order"""
        priority = 1  # Default
        
        # Hot leads get higher priority
        if customer.interest_level == 'hot':
            priority = 5
        elif customer.interest_level == 'warm':
            priority = 3
        elif customer.interest_level == 'cold':
            priority = 1
        
        # Recent interactions get boost
        if customer.last_interaction:
            days_since = (timezone.now() - customer.last_interaction).days
            if days_since < 7:
                priority += 1
        
        # Failed calls get lower priority
        if customer.total_calls > customer.successful_calls * 2:
            priority = max(1, priority - 1)
        
        return min(5, priority)  # Max priority is 5
    
    def _start_immediate_calls(self, campaign, count):
        """Start immediate calls for campaign"""
        contacts = campaign.contacts.filter(status='pending').order_by('-priority')[:count]
        
        for contact in contacts:
            contact.status = 'calling'
            contact.call_started_at = timezone.now()
            contact.save()
            
            # Trigger actual call
            self._initiate_call(contact)
    
    def _initiate_call(self, contact):
        """Actually initiate a call using Twilio"""
        try:
            agent = contact.campaign.ai_agent
            customer = contact.customer_profile
            
            # Create call session
            call_session = CallSession.objects.create(
                ai_agent=agent,
                customer_profile=customer,
                call_type='outbound',
                phone_number=customer.phone_number,
                outcome='calling',
                agent_notes=f'Auto campaign call - {contact.campaign.name}'
            )
            
            # Initialize Twilio call
            twilio_service = TwilioCallService()
            
            # Get personalized script for this customer
            personalized_script = agent.get_personalized_script_for_customer(customer)
            
            # Configure HumeAI for this call
            homeai_service = HomeAIService()
            
            # Start the call
            call_result = twilio_service.initiate_auto_call(
                to_number=customer.phone_number,
                agent_config={
                    'agent_id': str(agent.id),
                    'customer_id': str(customer.id),
                    'script': personalized_script,
                    'personality': agent.personality_type,
                    'voice_model': agent.voice_model
                },
                hume_ai_config={
                    'persona_id': agent.conversation_memory.get('homeai_persona_id'),
                    'learning_enabled': True
                }
            )
            
            if call_result.get('success'):
                call_session.twilio_call_sid = call_result.get('call_sid')
                call_session.connected_at = timezone.now()
                call_session.save()
                
                contact.twilio_call_sid = call_result.get('call_sid')
                contact.save()
                
                logger.info(f"Auto call initiated: {customer.phone_number} via {call_result.get('call_sid')}")
            else:
                contact.status = 'failed'
                contact.failure_reason = call_result.get('error', 'Unknown error')
                contact.save()
                
                call_session.outcome = 'failed'
                call_session.agent_notes = f"Call initiation failed: {contact.failure_reason}"
                call_session.save()
                
        except Exception as e:
            logger.error(f"Call initiation error: {str(e)}")
            contact.status = 'failed'
            contact.failure_reason = str(e)
            contact.save()
    
    def _calculate_success_rate(self, contacts):
        """Calculate campaign success rate"""
        completed = contacts.filter(status='completed')
        if not completed.exists():
            return 0
        
        successful = completed.filter(call_outcome__in=['interested', 'converted', 'callback_requested'])
        return round((successful.count() / completed.count()) * 100, 1)
    
    def _get_next_call_time(self, campaign):
        """Get next scheduled call time for campaign"""
        if campaign.status != 'active':
            return None
        
        # Find next pending contact
        next_contact = campaign.contacts.filter(status='pending').order_by('-priority', 'scheduled_datetime').first()
        
        if next_contact:
            return next_contact.scheduled_datetime.isoformat()
        
        return None


class StartImmediateCallsAPIView(APIView):
    """
    Start immediate calls manually
    Instant call execution
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Start calls immediately"""
        try:
            agent = request.user.ai_agent
            data = request.data
            
            # Get customers to call
            customer_phones = data.get('phone_numbers', [])
            call_count = data.get('call_count', 1)
            
            if customer_phones:
                # Call specific numbers
                customers = agent.customer_profiles.filter(
                    phone_number__in=customer_phones,
                    is_do_not_call=False
                )
            else:
                # Get next best customers to call
                customers = agent.customer_profiles.filter(
                    is_do_not_call=False,
                    is_converted=False
                ).order_by('-interest_level', '-last_interaction')[:call_count]
            
            calls_initiated = []
            
            for customer in customers:
                # Create call session
                call_session = CallSession.objects.create(
                    ai_agent=agent,
                    customer_profile=customer,
                    call_type='outbound',
                    phone_number=customer.phone_number,
                    outcome='calling',
                    agent_notes='Manual immediate call'
                )
                
                # Initiate call
                twilio_service = TwilioCallService()
                call_result = twilio_service.initiate_call(
                    to=customer.phone_number,
                    agent_config={
                        'script': agent.get_personalized_script_for_customer(customer),
                        'personality': agent.personality_type
                    }
                )
                
                if call_result.get('success'):
                    call_session.twilio_call_sid = call_result.get('call_sid')
                    call_session.connected_at = timezone.now()
                    call_session.save()
                    
                    calls_initiated.append({
                        'customer_phone': customer.phone_number,
                        'customer_name': customer.name,
                        'call_sid': call_result.get('call_sid'),
                        'status': 'initiated'
                    })
                else:
                    call_session.outcome = 'failed'
                    call_session.save()
            
            return Response({
                'message': f'Initiated {len(calls_initiated)} calls',
                'calls_initiated': calls_initiated,
                'total_requested': len(customers),
                'success_count': len(calls_initiated)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to start calls: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
