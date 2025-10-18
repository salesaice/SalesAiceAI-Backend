"""
Management command to test HumeAI + Twilio integration
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from HumeAiTwilio.models import HumeAgent, TwilioCall
from HumeAiTwilio.services import TwilioService

# Try to import decouple for .env loading
try:
    from decouple import config
    def get_env(key, default=None):
        import os
        return config(key, default=default or os.getenv(key))
except ImportError:
    import os
    def get_env(key, default=None):
        return os.getenv(key, default)

User = get_user_model()


class Command(BaseCommand):
    help = 'Test HumeAI + Twilio integration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='Phone number to call (with country code, e.g., +1234567890)',
        )
        parser.add_argument(
            '--agent-name',
            type=str,
            default='Test Agent',
            help='Name for the test agent',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting HumeAI + Twilio integration test...'))
        
        # Check environment variables
        self.stdout.write('\n1. Checking environment variables...')
        required_vars = [
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
            'TWILIO_PHONE_NUMBER',
            'HUME_AI_API_KEY',
            'HUME_CONFIG_ID'
        ]
        
        # Map alternative variable names
        var_mapping = {
            'HUME_AI_API_KEY': ['HUME_AI_API_KEY', 'HUME_AI_API_KEY'],
            'HUME_SECRET_KEY': ['HUME_AI_SECRET_KEY', 'HUME_SECRET_KEY']
        }
        
        missing_vars = []
        for var in required_vars:
            value = get_env(var)
            # Check alternative names
            if not value and var in var_mapping:
                for alt_var in var_mapping[var]:
                    value = get_env(alt_var)
                    if value:
                        break
            
            if not value:
                missing_vars.append(var)
                self.stdout.write(self.style.ERROR(f'  ✗ {var} not set'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {var} is set'))
        
        if missing_vars:
            self.stdout.write(self.style.ERROR('\nMissing environment variables. Please set them in .env file'))
            return
        
        # Create or get test agent
        self.stdout.write('\n2. Creating test agent...')
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('  ✗ No user found. Please create a user first.'))
            return
        
        agent, created = HumeAgent.objects.get_or_create(
            name=options['agent_name'],
            defaults={
                'description': 'Test agent for HumeAI + Twilio integration',
                'hume_config_id': get_env('HUME_CONFIG_ID'),
                'voice_name': 'ITO',
                'language': 'en',
                'system_prompt': 'You are a helpful sales assistant. Be friendly and professional.',
                'greeting_message': 'Hello! This is a test call from the AI system. How can I help you?',
                'status': 'active',
                'created_by': user
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Agent created: {agent.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Agent already exists: {agent.name}'))
        
        # Test Twilio service
        self.stdout.write('\n3. Testing Twilio service...')
        try:
            twilio_service = TwilioService()
            self.stdout.write(self.style.SUCCESS('  ✓ Twilio service initialized'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Twilio service error: {str(e)}'))
            return
        
        # Initiate test call if phone number provided
        if options['phone']:
            self.stdout.write(f'\n4. Initiating test call to {options["phone"]}...')
            
            try:
                # Note: This would actually make a real call
                # Be careful with this in production
                self.stdout.write(self.style.WARNING('  ⚠ Skipping actual call initiation in test mode'))
                self.stdout.write(self.style.WARNING('  ⚠ To make a real call, use the API endpoint'))
                
                # Example of what would be called:
                # result = twilio_service.initiate_call(
                #     to_number=options['phone'],
                #     agent=agent,
                #     callback_url='http://your-domain.com/api/hume-twilio/webhooks/twilio'
                # )
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Call initiation error: {str(e)}'))
                return
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('Setup Complete!'))
        self.stdout.write('='*50)
        self.stdout.write('\nAgent Details:')
        self.stdout.write(f'  ID: {agent.id}')
        self.stdout.write(f'  Name: {agent.name}')
        self.stdout.write(f'  Status: {agent.status}')
        self.stdout.write(f'  Voice: {agent.voice_name}')
        
        self.stdout.write('\nNext Steps:')
        self.stdout.write('1. Add "HumeAiTwilio" to INSTALLED_APPS in settings.py')
        self.stdout.write('2. Run: python manage.py makemigrations HumeAiTwilio')
        self.stdout.write('3. Run: python manage.py migrate')
        self.stdout.write('4. Add URL patterns to main urls.py:')
        self.stdout.write('   path("api/hume-twilio/", include("HumeAiTwilio.urls"))')
        self.stdout.write('5. Use the API to initiate calls:')
        self.stdout.write('   POST /api/hume-twilio/calls/')
        self.stdout.write('   {')
        self.stdout.write(f'     "to_number": "+1234567890",')
        self.stdout.write(f'     "agent_id": "{agent.id}",')
        self.stdout.write('     "customer_name": "Test Customer"')
        self.stdout.write('   }')
