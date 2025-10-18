# HumeAI + Twilio Integration Module

Complete Django app for integrating HumeAI voice agents with Twilio phone calls.

## Features

- ✅ **HumeAI Agent Management**: Create and manage AI agents with custom personalities
- ✅ **Twilio Call Handling**: Initiate and manage phone calls
- ✅ **Real-time Conversation**: Bidirectional audio streaming via WebSockets
- ✅ **Emotion Analysis**: Track customer emotions during calls
- ✅ **Call Analytics**: Comprehensive analytics and insights
- ✅ **Conversation Logging**: Store and retrieve conversation history
- ✅ **Webhook Handling**: Process events from Twilio and HumeAI
- ✅ **Dashboard APIs**: Get statistics and performance metrics

## Installation

### 1. Add to INSTALLED_APPS

Add `HumeAiTwilio` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'rest_framework',
    'channels',
    'HumeAiTwilio',
]
```

### 2. Configure Channels (for WebSocket support)

Add to `settings.py`:

```python
ASGI_APPLICATION = 'your_project.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}
```

### 3. Update urls.py

Add to your main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... other patterns
    path('api/hume-twilio/', include('HumeAiTwilio.urls')),
]
```

### 4. Run Migrations

```bash
python manage.py makemigrations HumeAiTwilio
python manage.py migrate
```

### 5. Test the Setup

```bash
python manage.py test_hume_twilio
```

## Environment Variables

Make sure these are set in your `.env` file:

```env
# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# HumeAI
HUME_API_KEY=your_api_key
HUME_SECRET_KEY=your_secret_key
HUME_CONFIG_ID=your_config_id
```

## API Endpoints

### Agents

- `GET /api/hume-twilio/agents/` - List all agents
- `POST /api/hume-twilio/agents/` - Create new agent
- `GET /api/hume-twilio/agents/{id}/` - Get agent details
- `PUT /api/hume-twilio/agents/{id}/` - Update agent
- `DELETE /api/hume-twilio/agents/{id}/` - Delete agent
- `GET /api/hume-twilio/agents/{id}/performance/` - Get performance metrics
- `POST /api/hume-twilio/agents/{id}/activate/` - Activate agent
- `POST /api/hume-twilio/agents/{id}/deactivate/` - Deactivate agent

### Calls

- `GET /api/hume-twilio/calls/` - List all calls
- `POST /api/hume-twilio/calls/` - Initiate new call
- `GET /api/hume-twilio/calls/{id}/` - Get call details
- `GET /api/hume-twilio/calls/{id}/conversation/` - Get conversation logs
- `GET /api/hume-twilio/calls/{id}/analytics/` - Get call analytics
- `POST /api/hume-twilio/calls/{id}/terminate/` - Terminate active call

### Dashboard

- `GET /api/hume-twilio/dashboard/stats/` - Get dashboard statistics
- `GET /api/hume-twilio/dashboard/recent-calls/` - Get recent calls

### Webhooks

- `POST /api/hume-twilio/webhooks/twilio/` - Twilio webhook
- `POST /api/hume-twilio/webhooks/twilio/twiml/` - TwiML generation
- `POST /api/hume-twilio/webhooks/hume/` - HumeAI webhook

## Usage Examples

### 1. Create an Agent

```python
import requests

response = requests.post('http://localhost:8000/api/hume-twilio/agents/', 
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    json={
        'name': 'Sales Agent',
        'description': 'AI agent for sales calls',
        'hume_config_id': 'your-config-id',
        'voice_name': 'ITO',
        'language': 'en',
        'system_prompt': 'You are a professional sales agent. Be friendly and helpful.',
        'greeting_message': 'Hello! How can I help you today?',
        'status': 'active'
    }
)

agent = response.json()
print(f"Agent created: {agent['id']}")
```

### 2. Initiate a Call

```python
response = requests.post('http://localhost:8000/api/hume-twilio/calls/',
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    json={
        'to_number': '+1234567890',
        'agent_id': 'agent-uuid-here',
        'customer_name': 'John Doe',
        'customer_email': 'john@example.com'
    }
)

call = response.json()
print(f"Call initiated: {call['call_sid']}")
```

### 3. Get Call Analytics

```python
call_id = 'your-call-uuid'
response = requests.get(f'http://localhost:8000/api/hume-twilio/calls/{call_id}/analytics/',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

analytics = response.json()
print(f"Sentiment: {analytics['overall_sentiment']}")
print(f"Total messages: {analytics['total_messages']}")
```

### 4. Get Dashboard Stats

```python
response = requests.get('http://localhost:8000/api/hume-twilio/dashboard/stats/?days=30',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

stats = response.json()
print(f"Total calls: {stats['total_calls']}")
print(f"Average duration: {stats['avg_duration']} seconds")
```

## Models

### HumeAgent
- Stores AI agent configurations
- Personality, voice settings, and behavior

### TwilioCall
- Records of all phone calls
- Status tracking and metadata

### ConversationLog
- Individual messages in conversations
- Emotion and sentiment data

### CallAnalytics
- Aggregated analytics per call
- Sentiment scores, metrics, and insights

### WebhookLog
- Logs of all webhook events
- For debugging and auditing

## Frontend Integration

Example React component for initiating calls:

```javascript
const initiateCall = async (phoneNumber, agentId) => {
  try {
    const response = await fetch('/api/hume-twilio/calls/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        to_number: phoneNumber,
        agent_id: agentId,
        customer_name: 'Customer Name'
      })
    });
    
    const data = await response.json();
    console.log('Call initiated:', data);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

## Support

For issues or questions, please check the documentation or contact support.

## License

Proprietary - All rights reserved
