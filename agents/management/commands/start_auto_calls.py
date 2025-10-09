from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from agents.ai_agent_models import AIAgent, CustomerProfile
from agents.auto_call_system import AutoCallCampaignAPIView
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Start automatic call campaigns for testing'
    
    def add_arguments(self, parser):
        parser.add_argument('--user-email', type=str, help='User email to start campaign for')
        parser.add_argument('--campaign-name', type=str, default='Test Campaign', help='Campaign name')
        parser.add_argument('--calls-per-hour', type=int, default=5, help='Number of calls per hour')
        parser.add_argument('--immediate-calls', type=int, default=2, help='Start immediate calls')
    
    def handle(self, *args, **options):
        user_email = options.get('user_email')
        
        if not user_email:
            self.stdout.write(self.style.ERROR('--user-email is required'))
            return
        
        try:
            user = User.objects.get(email=user_email)
            
            # Check if user has AI agent
            if not hasattr(user, 'ai_agent'):
                self.stdout.write(self.style.ERROR(f'User {user_email} does not have an AI agent'))
                return
            
            agent = user.ai_agent
            
            # Check if agent has customers
            customer_count = agent.customer_profiles.filter(is_do_not_call=False).count()
            
            if customer_count == 0:
                self.stdout.write(self.style.WARNING('No customers found. Creating sample customers...'))
                self.create_sample_customers(agent)
                customer_count = 3
            
            # Create auto call campaign
            campaign_data = {
                'campaign_name': options.get('campaign_name'),
                'campaign_type': 'test',
                'calls_per_hour': options.get('calls_per_hour'),
                'start_immediately': True,
                'immediate_call_count': options.get('immediate_calls'),
                'customer_filters': {
                    'interest_levels': ['warm', 'hot'],
                    'max_customers': min(customer_count, 10)
                },
                'call_schedule': {
                    'start_time': '09:00',
                    'end_time': '17:00'
                }
            }
            
            # Create campaign using API view
            from rest_framework.request import Request
            from django.http import HttpRequest
            
            # Create campaign directly using models instead of API view
            from agents.auto_campaign_models import AutoCallCampaign, AutoCampaignContact
            from django.utils import timezone
            
            # Create campaign directly
            campaign = AutoCallCampaign.objects.create(
                ai_agent=agent,
                name=campaign_data['campaign_name'],
                campaign_type=campaign_data['campaign_type'],
                status='active',
                target_customers=campaign_data['customer_filters']['max_customers'],
                calls_per_hour=campaign_data['calls_per_hour'],
                working_hours_start=campaign_data['call_schedule']['start_time'],
                working_hours_end=campaign_data['call_schedule']['end_time'],
                campaign_data=campaign_data
            )
            
            # Get customers and add to campaign
            customers = agent.customer_profiles.filter(
                is_do_not_call=False,
                interest_level__in=campaign_data['customer_filters']['interest_levels']
            )[:campaign_data['customer_filters']['max_customers']]
            
            campaign_contacts = []
            for customer in customers:
                campaign_contacts.append(AutoCampaignContact(
                    campaign=campaign,
                    customer_profile=customer,
                    status='pending',
                    priority=3 if customer.interest_level == 'hot' else 2,
                    scheduled_datetime=timezone.now()
                ))
            
            AutoCampaignContact.objects.bulk_create(campaign_contacts)
            
            # Create response data
            response_data = {
                'campaign_id': str(campaign.id),
                'campaign_name': campaign.name,
                'total_customers': len(campaign_contacts),
                'calls_per_hour': campaign.calls_per_hour,
                'status': campaign.status
            }
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Campaign created successfully!\n'
                    f'Campaign ID: {response_data["campaign_id"]}\n'
                    f'Campaign Name: {response_data["campaign_name"]}\n'
                    f'Total Customers: {response_data["total_customers"]}\n'
                    f'Calls Per Hour: {response_data["calls_per_hour"]}\n'
                    f'Status: {response_data["status"]}'
                )
            )
            
            self.stdout.write(
                self.style.WARNING(
                    f'\n📋 Next Steps:\n'
                    f'1. Start Celery worker: celery -A core worker --loglevel=info\n'
                    f'2. Start Celery beat: celery -A core beat --loglevel=info\n'
                    f'3. Configure HumeAI webhook: your-domain.com/agents/webhooks/hume-ai/\n'
                    f'4. Configure Twilio webhook: your-domain.com/agents/webhooks/twilio/\n'
                    f'5. Monitor campaign: GET /agents/ai/auto-campaigns/'
                )
            )
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with email {user_email} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
    
    def create_sample_customers(self, agent):
        """Create sample customers for testing"""
        sample_customers = [
            {
                'phone_number': '+1234567890',
                'name': 'John Smith',
                'interest_level': 'warm',
                'notes': 'Interested in product demo'
            },
            {
                'phone_number': '+1234567891', 
                'name': 'Sarah Johnson',
                'interest_level': 'hot',
                'notes': 'Ready to purchase, just needs pricing'
            },
            {
                'phone_number': '+1234567892',
                'name': 'Mike Chen',
                'interest_level': 'warm',
                'notes': 'Comparing options, follow up needed'
            }
        ]
        
        for customer_data in sample_customers:
            CustomerProfile.objects.create(
                ai_agent=agent,
                phone_number=customer_data['phone_number'],
                name=customer_data['name'],
                interest_level=customer_data['interest_level'],
                call_preference_time='anytime',
                conversation_notes={
                    'initial_notes': customer_data['notes'],
                    'source': 'management_command'
                }
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {len(sample_customers)} sample customers')
        )
