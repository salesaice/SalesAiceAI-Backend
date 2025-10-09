from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .ai_agent_models import AIAgent, CallSession
from .auto_campaign_models import AutoCallCampaign, AutoCampaignContact
from .auto_call_system import AutoCallCampaignAPIView

logger = logging.getLogger(__name__)


@shared_task
def process_scheduled_auto_calls():
    """
    Celery task to process scheduled automatic calls
    Har 5 minute mein run hota hai
    """
    logger.info("Processing scheduled auto calls...")
    
    # Get all active campaigns
    active_campaigns = AutoCallCampaign.objects.filter(status='active')
    
    total_calls_started = 0
    
    for campaign in active_campaigns:
        try:
            # Check if it's within working hours
            current_time = timezone.now().time()
            
            # Parse working hours
            start_time = datetime.strptime(campaign.working_hours_start, '%H:%M').time()
            end_time = datetime.strptime(campaign.working_hours_end, '%H:%M').time()
            
            if not (start_time <= current_time <= end_time):
                continue  # Skip if outside working hours
            
            # Calculate calls to make based on calls_per_hour
            minutes_passed = timezone.now().minute
            calls_this_interval = max(1, campaign.calls_per_hour // 12)  # 12 intervals per hour (5 min each)
            
            # Get pending contacts for this campaign
            pending_contacts = campaign.contacts.filter(
                status='pending',
                scheduled_datetime__lte=timezone.now()
            ).order_by('-priority', 'scheduled_datetime')[:calls_this_interval]
            
            # Start calls
            for contact in pending_contacts:
                try:
                    # Update contact status
                    contact.status = 'calling'
                    contact.call_started_at = timezone.now()
                    contact.save()
                    
                    # Initiate the actual call
                    auto_call_view = AutoCallCampaignAPIView()
                    auto_call_view._initiate_call(contact)
                    
                    total_calls_started += 1
                    
                    logger.info(f"Started auto call for {contact.customer_profile.phone_number}")
                    
                except Exception as e:
                    logger.error(f"Failed to start call for contact {contact.id}: {str(e)}")
                    contact.status = 'failed'
                    contact.failure_reason = str(e)
                    contact.save()
        
        except Exception as e:
            logger.error(f"Error processing campaign {campaign.id}: {str(e)}")
    
    logger.info(f"Scheduled auto calls completed. Started {total_calls_started} calls.")
    return {'calls_started': total_calls_started}


@shared_task
def process_callback_reminders():
    """
    Process scheduled callback reminders
    Customer ne callback manga tha to reminder
    """
    logger.info("Processing callback reminders...")
    
    # Get callbacks scheduled for now or overdue
    from .ai_agent_models import ScheduledCallback
    
    due_callbacks = ScheduledCallback.objects.filter(
        status='scheduled',
        scheduled_datetime__lte=timezone.now()
    ).select_related('ai_agent', 'customer_profile')
    
    callbacks_processed = 0
    
    for callback in due_callbacks:
        try:
            # Create call session for callback
            call_session = CallSession.objects.create(
                ai_agent=callback.ai_agent,
                customer_profile=callback.customer_profile,
                call_type='callback',
                phone_number=callback.customer_profile.phone_number,
                outcome='calling',
                agent_notes=f'Scheduled callback: {callback.reason}'
            )
            
            # Initiate callback call
            from .twilio_service import TwilioCallService
            twilio_service = TwilioCallService()
            
            # Use customer-specific script
            agent = callback.ai_agent
            personalized_script = agent.get_personalized_script_for_customer(callback.customer_profile)
            
            call_result = twilio_service.initiate_call(
                to=callback.customer_profile.phone_number,
                agent_config={
                    'script': f"Hi {callback.customer_profile.name}, you requested a callback. {personalized_script}",
                    'personality': agent.personality_type,
                    'callback_context': callback.reason
                }
            )
            
            if call_result.get('success'):
                call_session.twilio_call_sid = call_result.get('call_sid')
                call_session.connected_at = timezone.now()
                call_session.save()
                
                # Update callback status
                callback.status = 'in_progress'
                callback.call_session = call_session
                callback.save()
                
                callbacks_processed += 1
                logger.info(f"Started callback for {callback.customer_profile.phone_number}")
            
            else:
                # Callback failed - reschedule for later
                callback.scheduled_datetime = timezone.now() + timedelta(hours=1)
                callback.attempts += 1
                callback.save()
                
                call_session.outcome = 'failed'
                call_session.agent_notes = f"Callback failed: {call_result.get('error', 'Unknown error')}"
                call_session.save()
        
        except Exception as e:
            logger.error(f"Error processing callback {callback.id}: {str(e)}")
            callback.status = 'failed'
            callback.save()
    
    logger.info(f"Callback reminders completed. Processed {callbacks_processed} callbacks.")
    return {'callbacks_processed': callbacks_processed}


@shared_task
def cleanup_old_campaigns():
    """
    Cleanup old completed campaigns
    Database maintenance
    """
    logger.info("Cleaning up old campaigns...")
    
    # Mark campaigns as completed if all contacts are done
    active_campaigns = AutoCallCampaign.objects.filter(status='active')
    
    for campaign in active_campaigns:
        total_contacts = campaign.contacts.count()
        completed_contacts = campaign.contacts.filter(status__in=['completed', 'failed']).count()
        
        if total_contacts > 0 and completed_contacts == total_contacts:
            campaign.status = 'completed'
            campaign.completed_at = timezone.now()
            campaign.save()
            logger.info(f"Campaign {campaign.name} marked as completed")
    
    # Archive very old campaigns
    old_date = timezone.now() - timedelta(days=30)
    old_campaigns = AutoCallCampaign.objects.filter(
        status='completed',
        completed_at__lt=old_date
    )
    
    archived_count = old_campaigns.count()
    old_campaigns.update(status='archived')
    
    logger.info(f"Archived {archived_count} old campaigns")
    return {'archived_campaigns': archived_count}


@shared_task
def update_customer_priorities():
    """
    Update customer priorities based on recent interactions
    Customer behavior ke base par priority adjust karna
    """
    logger.info("Updating customer priorities...")
    
    from .ai_agent_models import CustomerProfile
    
    # Get customers who had recent interactions
    recent_date = timezone.now() - timedelta(days=7)
    recent_customers = CustomerProfile.objects.filter(
        last_interaction__gte=recent_date
    )
    
    updated_count = 0
    
    for customer in recent_customers:
        old_interest = customer.interest_level
        
        # Analyze recent call outcomes
        recent_calls = customer.call_sessions.filter(
            initiated_at__gte=recent_date
        ).order_by('-initiated_at')
        
        if recent_calls.exists():
            latest_call = recent_calls.first()
            
            # Update interest level based on latest call
            if latest_call.outcome == 'interested':
                customer.interest_level = 'hot'
            elif latest_call.outcome == 'callback_requested':
                customer.interest_level = 'warm'
            elif latest_call.outcome == 'not_interested':
                customer.interest_level = 'cold'
            
            # Save if changed
            if customer.interest_level != old_interest:
                customer.save()
                updated_count += 1
                logger.info(f"Updated {customer.phone_number}: {old_interest} → {customer.interest_level}")
    
    logger.info(f"Updated {updated_count} customer priorities")
    return {'customers_updated': updated_count}


# Celery Beat Schedule Configuration
"""
Add this to your settings.py:

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'process-auto-calls': {
        'task': 'agents.tasks.process_scheduled_auto_calls',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'process-callback-reminders': {
        'task': 'agents.tasks.process_callback_reminders', 
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'cleanup-old-campaigns': {
        'task': 'agents.tasks.cleanup_old_campaigns',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'update-customer-priorities': {
        'task': 'agents.tasks.update_customer_priorities',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
}

CELERY_TIMEZONE = 'UTC'
"""
