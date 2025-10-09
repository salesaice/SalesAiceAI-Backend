"""
Twilio Webhook Handlers for Real-time Agent Management Updates
"""
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from twilio.twiml.voice_response import VoiceResponse
import json
import logging

from .models_new import Agent, Campaign, CallQueue, Contact
from .subscription_utils import get_subscription_summary

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TwilioAgentWebhookView(View):
    """Handle Twilio webhooks for agent call status updates"""
    
    def post(self, request):
        """Process Twilio webhook for call status updates"""
        try:
            # Extract Twilio webhook data
            call_sid = request.POST.get('CallSid')
            call_status = request.POST.get('CallStatus')
            agent_id = request.POST.get('agent_id')  # Custom parameter
            campaign_id = request.POST.get('campaign_id')  # Custom parameter
            
            logger.info(f"Twilio webhook received: CallSid={call_sid}, Status={call_status}")
            
            # Process call status update
            if agent_id:
                self.update_agent_call_status(agent_id, call_sid, call_status, request.POST)
            
            if campaign_id:
                self.update_campaign_progress(campaign_id, call_sid, call_status, request.POST)
            
            return HttpResponse('OK', status=200)
            
        except Exception as e:
            logger.error(f"Error processing Twilio webhook: {str(e)}")
            return HttpResponse('Error', status=500)
    
    def update_agent_call_status(self, agent_id, call_sid, call_status, webhook_data):
        """Update agent call statistics based on Twilio webhook"""
        try:
            agent = Agent.objects.get(id=agent_id)
            
            # Update call metrics based on status
            if call_status == 'completed':
                agent.calls_handled += 1
                agent.total_calls += 1
                
                # Check if call was successful (you can customize this logic)
                call_duration = int(webhook_data.get('CallDuration', 0))
                if call_duration > 30:  # Consider calls > 30 seconds as successful
                    agent.successful_calls += 1
                
                # Update average call duration
                if agent.total_calls > 0:
                    current_avg = agent.average_call_duration or 0
                    new_avg = ((current_avg * (agent.total_calls - 1)) + call_duration) / agent.total_calls
                    agent.average_call_duration = round(new_avg, 2)
            
            elif call_status in ['failed', 'busy', 'no-answer']:
                agent.total_calls += 1
            
            # Update last activity
            agent.last_activity = timezone.now()
            agent.save()
            
            # Trigger dashboard update for user
            self.trigger_dashboard_update(agent.owner)
            
            logger.info(f"Updated agent {agent.name} call stats: {call_status}")
            
        except Agent.DoesNotExist:
            logger.error(f"Agent with ID {agent_id} not found")
        except Exception as e:
            logger.error(f"Error updating agent call status: {str(e)}")
    
    def update_campaign_progress(self, campaign_id, call_sid, call_status, webhook_data):
        """Update campaign progress based on Twilio webhook"""
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            
            # Update campaign metrics
            if call_status == 'completed':
                campaign.contacts_called += 1
                
                call_duration = int(webhook_data.get('CallDuration', 0))
                if call_duration > 30:
                    campaign.successful_calls += 1
                else:
                    campaign.failed_calls += 1
                
                # Update call queue entry if exists
                phone_number = webhook_data.get('To') or webhook_data.get('Called')
                if phone_number:
                    self.update_call_queue_entry(campaign, phone_number, call_status, webhook_data)
            
            elif call_status in ['failed', 'busy', 'no-answer']:
                campaign.contacts_called += 1
                campaign.failed_calls += 1
            
            campaign.save()
            
            # Check if campaign is complete
            if campaign.contacts_called >= campaign.total_contacts:
                campaign.status = 'completed'
                campaign.completed_at = timezone.now()
                campaign.save()
            
            logger.info(f"Updated campaign {campaign.name} progress: {call_status}")
            
        except Campaign.DoesNotExist:
            logger.error(f"Campaign with ID {campaign_id} not found")
        except Exception as e:
            logger.error(f"Error updating campaign progress: {str(e)}")
    
    def update_call_queue_entry(self, campaign, phone_number, call_status, webhook_data):
        """Update specific call queue entry"""
        try:
            # Find contact by phone number
            contact = Contact.objects.filter(
                agent=campaign.agent,
                phone__icontains=phone_number.replace('+', '').replace('-', '').replace(' ', '')[-10:]
            ).first()
            
            if not contact:
                return
            
            # Find and update queue entry
            queue_entry = CallQueue.objects.filter(
                campaign=campaign,
                contact=contact,
                status__in=['pending', 'in_progress']
            ).first()
            
            if queue_entry:
                if call_status == 'completed':
                    queue_entry.status = 'completed'
                    queue_entry.completed_at = timezone.now()
                    
                    call_duration = int(webhook_data.get('CallDuration', 0))
                    queue_entry.call_duration = call_duration
                    
                    # Update call outcome based on duration and other factors
                    if call_duration > 120:  # 2+ minutes might indicate engagement
                        queue_entry.call_outcome = 'engaged'
                        contact.call_outcome = 'engaged'
                    elif call_duration > 30:
                        queue_entry.call_outcome = 'answered'
                        contact.call_outcome = 'answered'
                    else:
                        queue_entry.call_outcome = 'brief_call'
                        contact.call_outcome = 'brief_call'
                
                elif call_status in ['failed', 'busy', 'no-answer']:
                    queue_entry.status = 'failed'
                    queue_entry.completed_at = timezone.now()
                    queue_entry.call_outcome = call_status
                    contact.call_outcome = call_status
                
                queue_entry.save()
                contact.call_status = 'completed'
                contact.last_call_attempt = timezone.now()
                contact.call_attempts += 1
                contact.save()
                
                logger.info(f"Updated queue entry for contact {contact.name}: {call_status}")
        
        except Exception as e:
            logger.error(f"Error updating call queue entry: {str(e)}")
    
    def trigger_dashboard_update(self, user):
        """Trigger dashboard update after call completion"""
        try:
            # Calculate updated statistics
            from .subscription_utils import get_subscription_summary
            
            agents = Agent.objects.filter(owner=user)
            total_agents = agents.count()
            active_agents = agents.filter(status='active').count()
            
            total_calls = sum(agent.total_calls for agent in agents)
            total_successful = sum(agent.successful_calls for agent in agents)
            avg_success_rate = round((total_successful / total_calls * 100)) if total_calls > 0 else 0
            
            subscription_info = get_subscription_summary(user)
            
            # Here you could trigger a notification or update cache
            # For now, we'll just log the update
            logger.info(f"Dashboard updated for user {user.email}: {total_calls} total calls")
            
        except Exception as e:
            logger.error(f"Error triggering dashboard update: {str(e)}")


@csrf_exempt
@require_POST
def twilio_voice_webhook(request):
    """Handle Twilio voice webhooks for agent calls"""
    try:
        agent_id = request.POST.get('agent_id')
        call_type = request.POST.get('call_type', 'inbound')
        
        response = VoiceResponse()
        
        # Get agent information
        if agent_id:
            try:
                agent = Agent.objects.get(id=agent_id)
                
                # Check if agent is active and within operating hours
                if agent.status != 'active':
                    response.say("This agent is currently not available. Please try again later.")
                    return HttpResponse(str(response), content_type='application/xml')
                
                # For inbound calls with auto-answer enabled
                if call_type == 'inbound' and agent.auto_answer_enabled:
                    # Use agent's sales script if available
                    script_text = agent.sales_script_text or "Hello, thank you for calling. How can I assist you today?"
                    response.say(script_text, voice=agent.voice_model)
                    
                    # Record the call
                    response.record(
                        max_length=300,  # 5 minutes max
                        action=f'/agents/webhooks/recording-complete/',
                        method='POST'
                    )
                else:
                    # Default greeting
                    response.say("Hello, thank you for calling. Please hold while we connect you.")
                
            except Agent.DoesNotExist:
                response.say("Invalid agent. Please check your configuration.")
        
        else:
            # Default response if no agent specified
            response.say("Thank you for calling. Please hold while we connect you to an agent.")
        
        return HttpResponse(str(response), content_type='application/xml')
        
    except Exception as e:
        logger.error(f"Error in voice webhook: {str(e)}")
        response = VoiceResponse()
        response.say("We're experiencing technical difficulties. Please try again later.")
        return HttpResponse(str(response), content_type='application/xml')


@csrf_exempt
@require_POST
def twilio_recording_complete(request):
    """Handle recording completion webhook"""
    try:
        recording_url = request.POST.get('RecordingUrl')
        call_sid = request.POST.get('CallSid')
        agent_id = request.POST.get('agent_id')
        
        if agent_id and recording_url:
            # Here you could save the recording URL to your database
            # or trigger further processing
            logger.info(f"Recording completed for agent {agent_id}: {recording_url}")
        
        return HttpResponse('OK')
        
    except Exception as e:
        logger.error(f"Error handling recording completion: {str(e)}")
        return HttpResponse('Error', status=500)


@csrf_exempt
def twilio_status_callback(request):
    """Handle Twilio status callbacks for real-time updates"""
    webhook_view = TwilioAgentWebhookView()
    return webhook_view.post(request)