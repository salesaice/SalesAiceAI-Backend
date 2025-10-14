"""
Utility functions for managing API keys (account-level vs agent-level)
"""
from django.conf import settings
from typing import Optional


def get_effective_hume_ai_key(agent) -> Optional[str]:
    """
    Get the effective Hume AI API key for an agent.
    
    Priority:
    1. Agent's custom key (if api_key_source='custom' and key exists)
    2. User's account default key
    3. System default from settings (if configured)
    
    Args:
        agent: Agent instance
        
    Returns:
        str: The API key to use, or None if no key available
    """
    # 1. Check if agent has custom key
    if (agent.api_key_source == 'custom' and 
        agent.hume_ai_api_key and 
        agent.hume_ai_api_key.strip()):
        return agent.hume_ai_api_key.strip()
    
    # 2. Check user's account default key
    if (hasattr(agent, 'owner') and 
        agent.owner and 
        hasattr(agent.owner, 'hume_ai_api_key') and
        agent.owner.hume_ai_api_key and 
        agent.owner.hume_ai_api_key.strip()):
        return agent.owner.hume_ai_api_key.strip()
    
    # 3. Check system default (optional)
    if hasattr(settings, 'DEFAULT_HUME_AI_KEY') and settings.DEFAULT_HUME_AI_KEY:
        return settings.DEFAULT_HUME_AI_KEY.strip()
    
    return None


def validate_api_key_setup(agent) -> dict:
    """
    Validate that the agent has a valid API key configuration.
    
    Returns:
        dict: {
            'valid': bool,
            'key_source': str,  # 'custom', 'account', 'system', or 'none'
            'message': str
        }
    """
    key = get_effective_hume_ai_key(agent)
    
    if not key:
        return {
            'valid': False,
            'key_source': 'none',
            'message': 'No Hume AI API key configured. Please set up account default or agent custom key.'
        }
    
    # Determine source
    if (agent.api_key_source == 'custom' and 
        agent.hume_ai_api_key and 
        agent.hume_ai_api_key.strip()):
        key_source = 'custom'
        message = 'Using agent-specific custom API key'
    elif (hasattr(agent, 'owner') and 
          agent.owner and 
          hasattr(agent.owner, 'hume_ai_api_key') and
          agent.owner.hume_ai_api_key and 
          agent.owner.hume_ai_api_key.strip()):
        key_source = 'account'
        message = 'Using account default API key'
    else:
        key_source = 'system'
        message = 'Using system default API key'
    
    return {
        'valid': True,
        'key_source': key_source,
        'message': message
    }


def get_api_key_status_for_user(user) -> dict:
    """
    Get API key status summary for a user.
    
    Returns:
        dict: {
            'has_account_key': bool,
            'agents_with_custom_keys': int,
            'agents_using_account_key': int,
            'agents_without_key': int
        }
    """
    has_account_key = bool(
        hasattr(user, 'hume_ai_api_key') and 
        user.hume_ai_api_key and 
        user.hume_ai_api_key.strip()
    )
    
    # Get user's agents
    agents = getattr(user, 'agent_set', []).all() if hasattr(user, 'agent_set') else []
    
    agents_with_custom = 0
    agents_using_account = 0
    agents_without_key = 0
    
    for agent in agents:
        validation = validate_api_key_setup(agent)
        if not validation['valid']:
            agents_without_key += 1
        elif validation['key_source'] == 'custom':
            agents_with_custom += 1
        else:
            agents_using_account += 1
    
    return {
        'has_account_key': has_account_key,
        'agents_with_custom_keys': agents_with_custom,
        'agents_using_account_key': agents_using_account,
        'agents_without_key': agents_without_key,
        'total_agents': len(agents)
    }