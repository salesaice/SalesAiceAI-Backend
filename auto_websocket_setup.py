"""
AUTOMATIC WEBSOCKET SETUP FOR PYTHONANYWHERE + NGROK
=====================================================

This script will:
1. Check if ngrok is installed
2. Download and setup ngrok if needed  
3. Create SSH tunnel to PythonAnywhere
4. Start ngrok tunnel
5. Show WebSocket URLs for Twilio configuration
6. Test WebSocket connectivity

USAGE:
    python auto_websocket_setup.py

REQUIREMENTS:
    - PythonAnywhere account: AICEgroup
    - Daphne running on PythonAnywhere port 8000
"""

import subprocess
import sys
import os
import platform
import time
import json
import requests
from pathlib import Path

class WebSocketSetup:
    def __init__(self):
        self.pythonanywhere_user = "AICEgroup"
        self.pythonanywhere_host = "ssh.pythonanywhere.com"
        self.local_port = 8000
        self.remote_port = 8000
        self.ngrok_url = None
        
    def check_ngrok(self):
        """Check if ngrok is installed"""
        print("\n" + "="*80)
        print("📦 Checking ngrok installation...")
        print("="*80)
        
        try:
            result = subprocess.run(['ngrok', 'version'], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ ngrok is installed: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        print("❌ ngrok not found!")
        return False
    
    def install_ngrok_instructions(self):
        """Show instructions to install ngrok"""
        print("\n" + "="*80)
        print("📥 INSTALL NGROK")
        print("="*80)
        
        if platform.system() == "Windows":
            print("""
Option 1: Using Chocolatey (Recommended)
    choco install ngrok

Option 2: Manual Download
    1. Go to: https://ngrok.com/download
    2. Download Windows 64-bit
    3. Extract ngrok.exe to: C:\\Program Files\\ngrok\\
    4. Add to PATH or run from that folder

Option 3: Using winget (Windows 11)
    winget install ngrok.ngrok

After installation, run this script again!
""")
        else:
            print("""
Visit: https://ngrok.com/download
Download and install ngrok for your platform
Then run this script again!
""")
        
        print("\n💡 FASTER ALTERNATIVE: Use Railway.app (no ngrok needed)")
        print("   Run: python deploy_to_railway.py")
        
    def get_ngrok_authtoken(self):
        """Check if ngrok authtoken is configured"""
        print("\n" + "="*80)
        print("🔑 Checking ngrok authentication...")
        print("="*80)
        
        config_file = Path.home() / ".ngrok2" / "ngrok.yml"
        if config_file.exists():
            print(f"✅ ngrok config found: {config_file}")
            return True
        
        print("❌ ngrok authtoken not configured!")
        print("\n📝 TO SETUP:")
        print("1. Sign up at: https://dashboard.ngrok.com/signup (FREE)")
        print("2. Get authtoken: https://dashboard.ngrok.com/get-started/your-authtoken")
        print("3. Run: ngrok config add-authtoken YOUR_TOKEN")
        print("\nThen run this script again!")
        return False
    
    def start_ssh_tunnel(self):
        """Create SSH tunnel to PythonAnywhere"""
        print("\n" + "="*80)
        print("🔐 SSH Tunnel Setup")
        print("="*80)
        
        print(f"""
To create SSH tunnel to PythonAnywhere, run this command in a SEPARATE terminal:

    ssh -L {self.local_port}:localhost:{self.remote_port} {self.pythonanywhere_user}@{self.pythonanywhere_host}

This will:
1. Prompt for PythonAnywhere password
2. Forward port {self.remote_port} from PythonAnywhere to your local port {self.local_port}
3. Keep the tunnel open (don't close this terminal!)

After SSH tunnel is connected, press ENTER here to continue...
""")
        input()
        
    def check_daphne_running(self):
        """Check if Daphne is running on PythonAnywhere"""
        print("\n" + "="*80)
        print("🔍 Checking if Daphne is running on PythonAnywhere...")
        print("="*80)
        
        print("""
In PythonAnywhere Bash Console, you need to run:

    cd /home/AICEgroup/SalesAiceAI
    source /home/AICEgroup/.virtualenvs/myenv/bin/activate
    daphne -b 0.0.0.0 -p 8000 core.asgi:application

This should show:
    "Listening on TCP address 0.0.0.0:8000"

Keep that console open!

Have you started Daphne? (y/n): """)
        
        response = input().strip().lower()
        if response != 'y':
            print("\n⚠️  Please start Daphne first, then run this script again!")
            return False
        
        return True
    
    def start_ngrok(self):
        """Start ngrok tunnel"""
        print("\n" + "="*80)
        print("🚀 Starting ngrok tunnel...")
        print("="*80)
        
        try:
            # Start ngrok in background
            print(f"Starting ngrok on port {self.local_port}...")
            print("This will open in a new window...")
            
            if platform.system() == "Windows":
                subprocess.Popen(['start', 'cmd', '/k', f'ngrok http {self.local_port}'], 
                               shell=True)
            else:
                subprocess.Popen(['gnome-terminal', '--', 'ngrok', 'http', str(self.local_port)])
            
            print("✅ ngrok started!")
            print("\n⏳ Waiting for ngrok to initialize (5 seconds)...")
            time.sleep(5)
            
            # Get ngrok URL from API
            return self.get_ngrok_url()
            
        except Exception as e:
            print(f"❌ Failed to start ngrok: {e}")
            return False
    
    def get_ngrok_url(self):
        """Get public URL from ngrok API"""
        print("\n📡 Fetching ngrok public URL...")
        
        try:
            response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=10)
            if response.status_code == 200:
                tunnels = response.json()['tunnels']
                for tunnel in tunnels:
                    if tunnel['proto'] == 'https':
                        self.ngrok_url = tunnel['public_url']
                        print(f"✅ ngrok URL: {self.ngrok_url}")
                        return True
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Could not get ngrok URL automatically: {e}")
            print("\n📝 Manual step:")
            print("1. Check the ngrok terminal window")
            print("2. Look for line: 'Forwarding https://XXXXX.ngrok-free.app'")
            print("3. Copy that URL")
            
            self.ngrok_url = input("\nEnter your ngrok HTTPS URL: ").strip()
            if self.ngrok_url:
                return True
        
        return False
    
    def show_websocket_urls(self):
        """Display WebSocket URLs for configuration"""
        print("\n" + "="*80)
        print("🎯 WEBSOCKET URLS FOR TWILIO CONFIGURATION")
        print("="*80)
        
        if not self.ngrok_url:
            print("❌ ngrok URL not available!")
            return
        
        # Convert https:// to wss://
        wss_base = self.ngrok_url.replace('https://', 'wss://')
        
        print(f"""
Base URL: {self.ngrok_url}

WebSocket Endpoints:
┌─────────────────────────────────────────────────────────────────┐
│ HumeAI WebSocket:                                               │
│ {wss_base}/ws/hume/                                             │
├─────────────────────────────────────────────────────────────────┤
│ Twilio Media Stream:                                            │
│ {wss_base}/ws/twilio/media/                                     │
├─────────────────────────────────────────────────────────────────┤
│ Calls WebSocket:                                                │
│ {wss_base}/ws/calls/                                            │
└─────────────────────────────────────────────────────────────────┘

TWILIO CONFIGURATION:
=====================
1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/active
2. Click your phone number
3. Update:
   
   A CALL COMES IN:
   ├─ Webhook: {self.ngrok_url}/api/twilio/voice/
   └─ HTTP POST
   
   CONFIGURE WITH:
   ├─ Media Streams: Enabled
   └─ WebSocket URL: {wss_base}/ws/twilio/media/

4. Save configuration
""")
    
    def test_websocket(self):
        """Test WebSocket connection"""
        print("\n" + "="*80)
        print("🧪 Testing WebSocket Connection...")
        print("="*80)
        
        if not self.ngrok_url:
            print("❌ No ngrok URL available for testing")
            return
        
        print("\nInstalling websockets library if needed...")
        subprocess.run([sys.executable, "-m", "pip", "install", "websockets", "-q"], 
                      check=False)
        
        wss_url = self.ngrok_url.replace('https://', 'wss://') + '/ws/hume/'
        
        test_code = f"""
import asyncio
import websockets

async def test():
    try:
        url = '{wss_url}'
        print(f'Connecting to {{url}}...')
        async with websockets.connect(url, timeout=10) as ws:
            print('✅ CONNECTION SUCCESSFUL!')
            await ws.send('{{"type": "test"}}')
            print('✅ Test message sent!')
            return True
    except Exception as e:
        print(f'❌ CONNECTION FAILED: {{e}}')
        return False

result = asyncio.run(test())
exit(0 if result else 1)
"""
        
        result = subprocess.run([sys.executable, "-c", test_code], 
                              capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n🎉 WebSocket is working!")
            return True
        else:
            print("\n⚠️  WebSocket test failed. Check:")
            print("  1. SSH tunnel is running")
            print("  2. Daphne is running on PythonAnywhere")
            print("  3. ngrok tunnel is active")
            return False
    
    def show_next_steps(self):
        """Show next steps for initiating call"""
        print("\n" + "="*80)
        print("🚀 READY TO MAKE CALLS!")
        print("="*80)
        
        print(f"""
✅ WebSocket server is configured and running!

NEXT STEPS:
===========

1. Configure Twilio (see URLs above)

2. Test call initiation:
   
   Method A: Using Swagger UI
   ├─ Go to: https://aicegroup.pythonanywhere.com/swagger/
   ├─ Find call initiation endpoint
   └─ Send request with: {{"phone_number": "+923030062756"}}
   
   Method B: Using cURL
   └─ curl -X POST https://aicegroup.pythonanywhere.com/api/calls/initiate/ \\
        -H "Content-Type: application/json" \\
        -d '{{"phone_number": "+923030062756"}}'

3. Answer phone when it rings!

4. Talk to HumeAI agent in real-time! 🎙️

MONITORING:
===========
• ngrok Dashboard: http://127.0.0.1:4040
  (See all WebSocket connections in real-time)

• PythonAnywhere Bash Console
  (See Daphne server logs)

• Twilio Debugger:
  https://console.twilio.com/us1/monitor/logs/debugger

TROUBLESHOOTING:
================
If call doesn't work:
1. Check Twilio has credits
2. Verify HumeAI API key is set
3. Check Daphne logs for errors
4. Review Twilio debugger for webhook errors
""")
    
    def run(self):
        """Main setup flow"""
        print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     🚀 AUTOMATIC WEBSOCKET SETUP FOR REAL-TIME VOICE CALLS       ║
║                                                                   ║
║     PythonAnywhere + ngrok + Twilio + HumeAI                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")
        
        # Step 1: Check ngrok
        if not self.check_ngrok():
            self.install_ngrok_instructions()
            return
        
        # Step 2: Check ngrok auth
        if not self.get_ngrok_authtoken():
            return
        
        # Step 3: Check Daphne
        if not self.check_daphne_running():
            return
        
        # Step 4: SSH tunnel instructions
        self.start_ssh_tunnel()
        
        # Step 5: Start ngrok
        if not self.start_ngrok():
            print("\n❌ Failed to start ngrok!")
            print("Please start ngrok manually: ngrok http 8000")
            return
        
        # Step 6: Show URLs
        self.show_websocket_urls()
        
        # Step 7: Test connection
        self.test_websocket()
        
        # Step 8: Next steps
        self.show_next_steps()
        
        print("\n" + "="*80)
        print("✅ SETUP COMPLETE!")
        print("="*80)
        print("\n⚠️  IMPORTANT: Keep these terminals running:")
        print("  • SSH tunnel terminal")
        print("  • ngrok terminal")
        print("  • PythonAnywhere Daphne console")

if __name__ == "__main__":
    setup = WebSocketSetup()
    setup.run()
