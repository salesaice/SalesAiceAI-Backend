"""
AGENT VALIDATION AND SETUP HELPER
Agent ID validation aur proper setup ke liye
"""

from agents.models import Agent
import logging

logger = logging.getLogger(__name__)

def validate_and_get_agent(agent_id, user=None):
    """
    Agent ID validate kar ke proper agent return karta hai
    Logs mein 'Agent not found' error fix karne ke liye
    """
    try:
        logger.info(f"🔍 Validating agent ID: {agent_id}")
        
        # Try to find agent by ID
        if user:
            # User's own agents only
            agent = Agent.objects.get(
                id=agent_id,
                owner=user,
                status='active'
            )
        else:
            # Any active agent
            agent = Agent.objects.get(
                id=agent_id,
                status='active'
            )
        
        logger.info(f"✅ Agent found: {agent.name} (ID: {agent.id})")
        logger.info(f"   Type: {agent.agent_type}")
        logger.info(f"   Status: {agent.status}")
        logger.info(f"   Voice Tone: {getattr(agent, 'voice_tone', 'Not set')}")
        
        # Check if agent has sales script
        has_sales_script = hasattr(agent, 'sales_script_text') and agent.sales_script_text
        logger.info(f"   Has Sales Script: {has_sales_script}")
        
        if has_sales_script:
            script_preview = agent.sales_script_text[:100] + "..." if len(agent.sales_script_text) > 100 else agent.sales_script_text
            logger.info(f"   Sales Script Preview: {script_preview}")
        
        return agent
        
    except Agent.DoesNotExist:
        logger.error(f"❌ Agent not found with ID: {agent_id}")
        
        # List available agents for debugging
        if user:
            available_agents = Agent.objects.filter(owner=user, status='active')
        else:
            available_agents = Agent.objects.filter(status='active')[:5]  # Limit to 5 for logs
        
        logger.info("📋 Available agents:")
        for agent in available_agents:
            logger.info(f"   - {agent.name} (ID: {agent.id}) - Type: {agent.agent_type}")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Agent validation error: {str(e)}")
        return None


def create_default_agent_if_missing(user):
    """
    Agar user ka koi agent nahi hai toh default agent create karta hai
    """
    try:
        # Check if user has any agents
        user_agents = Agent.objects.filter(owner=user, status='active')
        
        if user_agents.exists():
            logger.info(f"User {user.email} already has {user_agents.count()} agent(s)")
            return user_agents.first()
        
        # Create default agent
        default_agent = Agent.objects.create(
            owner=user,
            name=f"{user.get_full_name() or user.email}'s Voice Agent",
            agent_type='both',  # Can handle both inbound and outbound
            status='active',
            voice_tone='professional',
            description='Default voice agent for sales calls',
            sales_script_text=f"""Hello [NAME]! This is {user.get_full_name() or 'your assistant'} calling from [COMPANY]. 

I hope you're having a great day! I'm reaching out because I have something that could really benefit you. 

We've been helping people just like you achieve amazing results with [PRODUCT], and I thought you might be interested.

What I'd love to do is learn more about your current situation and see if this could be a good fit for you. What's your biggest priority right now?""",
            business_info={
                'company_name': 'Your Company',
                'product_name': 'AI Voice Solutions',
                'contact_email': user.email
            }
        )
        
        logger.info(f"✅ Created default agent for user {user.email}: {default_agent.name} (ID: {default_agent.id})")
        
        return default_agent
        
    except Exception as e:
        logger.error(f"❌ Default agent creation error: {str(e)}")
        return None


def get_user_agent_for_call(user, agent_id=None):
    """
    Call ke liye proper agent return karta hai
    Agent ID nahi mila toh default agent create/use karta hai
    """
    try:
        if agent_id:
            # Specific agent requested
            agent = validate_and_get_agent(agent_id, user)
            if agent:
                return agent
            else:
                logger.warning(f"Requested agent {agent_id} not found, using fallback")
        
        # No specific agent or agent not found - get/create default
        user_agents = Agent.objects.filter(owner=user, status='active')
        
        if user_agents.exists():
            agent = user_agents.first()
            logger.info(f"Using user's first available agent: {agent.name} (ID: {agent.id})")
            return agent
        else:
            # Create default agent
            agent = create_default_agent_if_missing(user)
            return agent
            
    except Exception as e:
        logger.error(f"❌ Agent selection error: {str(e)}")
        return None


def list_user_agents(user):
    """User ke sab agents list karta hai debugging ke liye"""
    try:
        agents = Agent.objects.filter(owner=user)
        
        logger.info(f"📋 User {user.email} agents:")
        for agent in agents:
            logger.info(f"   - {agent.name} (ID: {agent.id})")
            logger.info(f"     Type: {agent.agent_type}, Status: {agent.status}")
            
            if hasattr(agent, 'sales_script_text') and agent.sales_script_text:
                script_length = len(agent.sales_script_text)
                logger.info(f"     Sales Script: {script_length} characters")
            else:
                logger.info(f"     Sales Script: None")
        
        return agents
        
    except Exception as e:
        logger.error(f"❌ Agent listing error: {str(e)}")
        return Agent.objects.none()