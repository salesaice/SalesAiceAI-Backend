from django.urls import path, include
from . import views
from .ai_agent_views import (
    AIAgentSetupAPIView,
    AIAgentTrainingAPIView,
    AIAgentCallManagementAPIView,
    StartAICallAPIView,
    CallOutcomeAPIView,
    DynamicAgentLearningAPIView
)
from .ai_agent_crud import (
    AIAgentListCreateAPIView,
    AIAgentDetailAPIView,
    AIAgentBulkActionsAPIView,
    AIAgentStatsAPIView
)
from .customer_callback_crud import (
    CustomerProfileCRUDAPIView,
    CustomerProfileDetailAPIView,
    ScheduledCallbackCRUDAPIView,
    ScheduledCallbackDetailAPIView,
    CallbackBulkActionsAPIView
)
from .real_time_learning import (
    RealTimeCallLearningAPIView,
    AutoCallAnalysisAPIView
)
from .auto_call_system import (
    AutoCallCampaignAPIView,
    StartImmediateCallsAPIView
)
from .webhook_integration import (
    hume_ai_webhook,
    twilio_webhook,
    twilio_voice_webhook,
    twilio_status_webhook,
    manual_learning_trigger
)

urlpatterns = [
    # Traditional Agent APIs
    path('profile/', views.AgentProfileAPIView.as_view(), name='agent-profile'),
    path('status/', views.AgentStatusAPIView.as_view(), name='agent-status'),
    path('performance/', views.AgentPerformanceAPIView.as_view(), name='agent-performance'),
    path('call-history/', views.AgentCallHistoryAPIView.as_view(), name='agent-call-history'),
    
    # AI Agent CRUD Operations - Complete System
    path('ai/', AIAgentListCreateAPIView.as_view(), name='ai-agent-list-create'),
    path('ai/<uuid:id>/', AIAgentDetailAPIView.as_view(), name='ai-agent-detail'),
    path('ai/bulk-actions/', AIAgentBulkActionsAPIView.as_view(), name='ai-agent-bulk-actions'),
    path('ai/stats/', AIAgentStatsAPIView.as_view(), name='ai-agent-stats'),
    
    # AI Agent Management - Specific Operations
    path('ai/setup/', AIAgentSetupAPIView.as_view(), name='ai-agent-setup'),
    path('ai/training/', AIAgentTrainingAPIView.as_view(), name='ai-agent-training'),
    path('ai/calls/', AIAgentCallManagementAPIView.as_view(), name='ai-agent-calls'),
    path('ai/start-call/', StartAICallAPIView.as_view(), name='ai-start-call'),
    path('ai/call-outcome/', CallOutcomeAPIView.as_view(), name='ai-call-outcome'),
    path('ai/dynamic-learning/', DynamicAgentLearningAPIView.as_view(), name='dynamic-agent-learning'),
    
    # Real-time Learning APIs
    path('ai/real-time-learning/', RealTimeCallLearningAPIView.as_view(), name='real-time-learning'),
    path('ai/auto-call-analysis/', AutoCallAnalysisAPIView.as_view(), name='auto-call-analysis'),
    
    # Webhook Integration for Automatic Learning
    path('webhooks/hume-ai/', hume_ai_webhook, name='hume-ai-webhook'),
    path('webhooks/twilio/', twilio_webhook, name='twilio-webhook'),
    path('webhooks/twilio/voice/', twilio_voice_webhook, name='twilio-voice-webhook'),
    path('webhooks/twilio/status/', twilio_status_webhook, name='twilio-status-webhook'),
    path('webhooks/manual-trigger/', manual_learning_trigger, name='manual-learning-trigger'),
    
    # Customer Profile CRUD
    path('ai/customers/', CustomerProfileCRUDAPIView.as_view(), name='customer-profile-list-create'),
    path('ai/customers/<uuid:id>/', CustomerProfileDetailAPIView.as_view(), name='customer-profile-detail'),
    
    # Scheduled Callback CRUD
    path('ai/callbacks/', ScheduledCallbackCRUDAPIView.as_view(), name='callback-list-create'),
    path('ai/callbacks/<uuid:id>/', ScheduledCallbackDetailAPIView.as_view(), name='callback-detail'),
    path('ai/callbacks/bulk-actions/', CallbackBulkActionsAPIView.as_view(), name='callback-bulk-actions'),
    
    # Auto Call System
    path('ai/auto-campaigns/', AutoCallCampaignAPIView.as_view(), name='auto-call-campaigns'),
    path('ai/start-immediate-calls/', StartImmediateCallsAPIView.as_view(), name='start-immediate-calls'),
    
    # Agent Management & Configuration System (16 hours of features)
    path('', include('agents.agent_management_urls')),
]
