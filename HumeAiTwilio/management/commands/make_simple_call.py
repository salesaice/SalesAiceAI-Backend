"""
Make test call - Simple version (NO WebSocket)
For FREE PythonAnywhere deployment
"""

from django.core.management.base import BaseCommand
from HumeAiTwilio.models import HumeAgent
from HumeAiTwilio.twilio_simple_voice import initiate_outbound_call_simple


class Command(BaseCommand):
    help = 'Make a test call using simple HTTP version (NO WebSocket required)'

    def add_arguments(self, parser):
        parser.add_argument('phone_number', type=str, help='Phone number to call (e.g., +1234567890)')
        parser.add_argument('--agent-id', type=int, help='Specific agent ID to use')

    def handle(self, *args, **options):
        phone_number = options['phone_number']
        agent_id = options.get('agent_id')
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS('🚀 MAKING TEST CALL (Simple HTTP - No WebSocket)'))
        self.stdout.write("=" * 70)
        
        # Get agent
        if agent_id:
            try:
                agent = HumeAgent.objects.get(id=agent_id)
            except HumeAgent.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Agent with ID {agent_id} not found!'))
                return
        else:
            agent = HumeAgent.objects.filter(is_active=True).first()
            if not agent:
                self.stdout.write(self.style.ERROR('❌ No active agent found!'))
                self.stdout.write('Please create an agent in Django admin:')
                self.stdout.write('  python manage.py createsuperuser')
                self.stdout.write('  Go to /admin/ → HumeAi Twilio → Hume Agents → Add')
                return
        
        self.stdout.write(f"\n📞 Calling: {phone_number}")
        self.stdout.write(f"🤖 Agent: {agent.name}")
        self.stdout.write(f"⚙️  Mode: Simple HTTP (FREE PythonAnywhere compatible)")
        
        try:
            call = initiate_outbound_call_simple(phone_number, agent.id)
            
            if call:
                self.stdout.write("\n" + "=" * 70)
                self.stdout.write(self.style.SUCCESS('✅ CALL INITIATED SUCCESSFULLY!'))
                self.stdout.write("=" * 70)
                self.stdout.write(f"Call SID: {call.twilio_call_sid}")
                self.stdout.write(f"Call ID: {call.call_id}")
                self.stdout.write(f"Agent: {agent.name}")
                self.stdout.write(f"Status: {call.status}")
                self.stdout.write("\n📱 The phone should ring now!")
                self.stdout.write("🎙️  Answer and speak to the AI agent")
                self.stdout.write("\n⚠️  Note: This is simple HTTP version with 1-2 sec delay")
                self.stdout.write("   For real-time: Upgrade PythonAnywhere & use WebSocket version")
                self.stdout.write("=" * 70)
            else:
                self.stdout.write(self.style.ERROR('❌ Failed to initiate call'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            self.stdout.write('\nTroubleshooting:')
            self.stdout.write('1. Check Twilio credentials in .env')
            self.stdout.write('2. Verify phone number format (+1234567890)')
            self.stdout.write('3. Check Twilio account balance')
            self.stdout.write('4. Update webhook URLs in Twilio console')
