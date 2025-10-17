"""
🎯 HUME AI VOICE AGENT INTEGRATION
Proper HumeAI Voice Agent setup with agent database content
"""

import os
import django
import requests
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from agents.models import Agent

class HumeAIVoiceIntegration:
    """
    Proper HumeAI Voice Agent integration with caching
    """
    
    # Class-level cache for agent configs (prevents recreating same agent)
    _agent_config_cache = {}
    
    def __init__(self):
        self.api_key = "mb5K22hbrOAvddJfkP4ZlScpMVHItgw0jfyxj0F1byGJ7j1w"
        self.base_url = "https://api.hume.ai/v0"
        
    def create_voice_agent_config(self, agent_from_db):
        """
        Create HumeAI Voice Agent config using agent database content
        """
        try:
            # Get agent content from database
            sales_script = agent_from_db.sales_script_text if agent_from_db.sales_script_text else "Hello! How can I help you today?"
            
            # Build knowledge base from agent files
            knowledge_content = ""
            if hasattr(agent_from_db, 'knowledge_files') and agent_from_db.knowledge_files:
                for file_info in agent_from_db.knowledge_files:
                    if 'content' in file_info:
                        knowledge_content += file_info['content'] + "\n\n"
            
            # Business context
            business_context = ""
            if hasattr(agent_from_db, 'business_info') and agent_from_db.business_info:
                business_info = agent_from_db.business_info
                business_context = f"""
                Company: {business_info.get('name', 'Our Company')}
                Industry: {business_info.get('industry', 'Business Solutions')}
                Mission: {business_info.get('mission', 'Helping businesses grow')}
                """
            
            # Create HumeAI Voice Agent configuration
            config_data = {
                "name": f"Voice Agent - {agent_from_db.name}",
                "voice": {
                    "provider": "HUME_AI", 
                    "name": "Inspiring Woman" if 'female' in agent_from_db.voice_model.lower() else "Confident Man",
                    "language": "en-US"
                },
                "system_prompt": f"""
                You are {agent_from_db.name}, a professional sales consultant.
                
                OPENING SCRIPT (use this when call starts):
                {sales_script}
                
                KNOWLEDGE BASE (use this to answer questions):
                {knowledge_content}
                
                BUSINESS CONTEXT:
                {business_context}
                
                INSTRUCTIONS:
                - Always use the opening script when the call starts
                - Answer questions using only the knowledge base provided
                - If you don't know something from the knowledge base, ask for clarification
                - Be professional and helpful
                - Keep responses conversational and natural
                """,
                "language_model": {
                    "model_provider": "ANTHROPIC",
                    "model_resource": "claude-3-5-sonnet-20241022"
                },
                "tools": [],
                "ellm_configuration": {
                    "model": "claude-3-5-sonnet-20241022"
                }
            }
            
            print(f"✅ Created HumeAI config for agent: {agent_from_db.name}")
            return config_data
            
        except Exception as e:
            print(f"❌ Error creating HumeAI config: {e}")
            return None
    
    def create_voice_agent(self, agent_from_db):
        """
        Create actual HumeAI Voice Agent using agent database
        WITH CACHING - Only creates new agent if not exists or data changed
        """
        try:
            # Create cache key from agent data
            cache_key = f"{agent_from_db.id}_{agent_from_db.name}"
            
            # Check if we already have a config for this agent
            if cache_key in self._agent_config_cache:
                cached_config = self._agent_config_cache[cache_key]
                print(f"✅ Using cached HumeAI config for agent: {agent_from_db.name}")
                print(f"   Config ID: {cached_config['config_id']}")
                print(f"   Created: {cached_config['created_at']}")
                return cached_config
            
            # If not cached, create new config
            config = self.create_voice_agent_config(agent_from_db)
            if not config:
                return None
                
            headers = {
                "X-Hume-Api-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Create the voice agent
            response = requests.post(
                f"{self.base_url}/evi/configs",
                headers=headers,
                json=config,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                config_id = result.get('id')
                
                print(f"✅ NEW HumeAI Voice Agent created successfully!")
                print(f"   Config ID: {config_id}")
                print(f"   Agent Name: {agent_from_db.name}")
                
                # Cache the result
                cached_result = {
                    'success': True,
                    'config_id': config_id,
                    'agent_name': agent_from_db.name,
                    'voice_config': result,
                    'created_at': datetime.now().isoformat()
                }
                
                self._agent_config_cache[cache_key] = cached_result
                print(f"   📦 Config cached for future calls")
                
                return cached_result
            else:
                print(f"❌ HumeAI API error: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating HumeAI Voice Agent: {e}")
            return None
    
    def start_voice_call(self, config_id, phone_number):
        """
        Start HumeAI voice call using created agent
        """
        try:
            headers = {
                "X-Hume-Api-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            call_data = {
                "config_id": config_id,
                "phone_number": phone_number
            }
            
            response = requests.post(
                f"{self.base_url}/evi/chat",
                headers=headers,
                json=call_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"✅ HumeAI voice call started to {phone_number}")
                return result
            else:
                print(f"❌ Call start error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error starting voice call: {e}")
            return None

# Usage example
def setup_hume_voice_agent():
    """
    Setup HumeAI Voice Agent with agent database content
    """
    try:
        # Get agent from database - specifically Sales AICE AI Agent
        agent = Agent.objects.filter(name="Sales AICE AI Agent", status='active').first()
        
        if not agent:
            # Fallback to any agent with content
            agent = Agent.objects.filter(status='active').exclude(sales_script_text='').exclude(sales_script_text__isnull=True).first()
            
        if not agent:
            print("❌ No active agent found in database with content")
            return None
        
        print(f"🔧 Setting up HumeAI Voice Agent for: {agent.name}")
        
        # Create HumeAI integration
        hume_integration = HumeAIVoiceIntegration()
        
        # Create voice agent with database content
        result = hume_integration.create_voice_agent(agent)
        
        if result and result['success']:
            config_id = result['config_id']
            
            print(f"🎉 SUCCESS! HumeAI Voice Agent ready!")
            print(f"   Agent Name: {agent.name}")
            print(f"   Config ID: {config_id}")
            print(f"   Sales Script: {len(agent.sales_script_text)} characters")
            print(f"   Knowledge Files: {len(agent.knowledge_files)} files")
            
            return {
                'config_id': config_id,
                'agent': agent,
                'ready': True
            }
        else:
            print("❌ Failed to create HumeAI Voice Agent")
            return None
            
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return None

if __name__ == "__main__":
    print("🚀 HUME AI VOICE AGENT SETUP")
    print("=" * 50)
    
    result = setup_hume_voice_agent()
    
    if result:
        print("\n📞 NEXT STEPS:")
        print("1. Use Config ID for Twilio webhook")
        print("2. Agent will use database sales script")
        print("3. Answers will come from knowledge files")
        print("4. HumeAI will handle real conversation")
    else:
        print("\n❌ Setup failed - check agent database")