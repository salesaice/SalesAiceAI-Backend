"""
Management command to make test calls using Twilio + HumeAI
"""

from django.core.management.base import BaseCommand
from decouple import config
from HumeAiTwilio.twilio_voice_bridge import initiate_outbound_call
from HumeAiTwilio.models import HumeAgent


class Command(BaseCommand):
    help = 'Make a test call using Twilio + HumeAI integration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'phone_number',
            type=str,
            help='Phone number to call (e.g., +1234567890)'
        )
        parser.add_argument(
            '--agent',
            type=str,
            help='Agent ID to use (optional)',
            default=None
        )
    
    def handle(self, *args, **options):
        phone_number = options['phone_number']
        agent_id = options.get('agent')
        
        self.stdout.write("="*80)
        self.stdout.write(self.style.SUCCESS("📞 TWILIO + HUMEAI TEST CALL"))
        self.stdout.write("="*80)
        
        # Check environment
        twilio_sid = config('TWILIO_ACCOUNT_SID', default='')
        twilio_number = config('TWILIO_PHONE_NUMBER', default='')
        hume_key = config('HUME_AI_API_KEY', default=config('HUME_API_KEY', default=''))
        
        if not all([twilio_sid, twilio_number, hume_key]):
            self.stdout.write(self.style.ERROR("\n❌ Missing configuration!"))
            self.stdout.write("Required in .env:")
            self.stdout.write("  - TWILIO_ACCOUNT_SID")
            self.stdout.write("  - TWILIO_AUTH_TOKEN")
            self.stdout.write("  - TWILIO_PHONE_NUMBER")
            self.stdout.write("  - HUME_AI_API_KEY")
            return
        
        self.stdout.write(f"\n✅ Twilio SID: {twilio_sid[:10]}...")
        self.stdout.write(f"✅ Twilio Number: {twilio_number}")
        self.stdout.write(f"✅ HumeAI Key: {hume_key[:10]}...")
        
        # List agents
        agents = HumeAgent.objects.filter(status='active')
        self.stdout.write(f"\n📋 Active Agents: {agents.count()}")
        
        for agent in agents:
            self.stdout.write(f"  - {agent.name} (ID: {agent.id})")
        
        # Make call
        self.stdout.write(f"\n📞 Calling: {phone_number}")
        self.stdout.write("Please wait...\n")
        
        try:
            result = initiate_outbound_call(phone_number, agent_id)
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS("\n✅ CALL INITIATED SUCCESSFULLY!"))
                self.stdout.write(f"Call SID: {result['call_sid']}")
                self.stdout.write(f"Call ID: {result['call_id']}")
                self.stdout.write(f"Agent: {result['agent']}")
                self.stdout.write(f"Status: {result['status']}")
                
                self.stdout.write("\n" + "="*80)
                self.stdout.write("📱 NEXT STEPS:")
                self.stdout.write("="*80)
                self.stdout.write("1. Answer the phone when it rings")
                self.stdout.write("2. Listen to the greeting")
                self.stdout.write("3. Start speaking to the AI agent")
                self.stdout.write("4. The conversation will be logged in the database")
                self.stdout.write("\n5. View call details:")
                self.stdout.write("   python manage.py runserver")
                self.stdout.write("   http://127.0.0.1:8000/admin/")
            else:
                self.stdout.write(self.style.ERROR(f"\n❌ CALL FAILED!"))
                self.stdout.write(f"Error: {result['error']}")
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ ERROR: {e}"))
            import traceback
            traceback.print_exc()
