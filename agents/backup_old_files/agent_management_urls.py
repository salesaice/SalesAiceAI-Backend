from django.urls import path
from . import agent_management_views, voice_call_integration

urlpatterns = [
    # Agent Management URLs
    path('management/list/', agent_management_views.agent_list_page, name='agent-list-page'),
    path('management/create/', agent_management_views.create_edit_agent, name='create-agent'),
    path('management/edit/', agent_management_views.create_edit_agent, name='edit-agent'),
    path('management/<uuid:agent_id>/settings/', agent_management_views.agent_settings, name='agent-settings'),
    path('management/<uuid:agent_id>/delete/', agent_management_views.delete_agent, name='delete-agent'),
    
    # HomeAI Voice Configuration URLs
    path('management/<uuid:agent_id>/voice/', voice_call_integration.agent_voice_configuration, name='agent-voice-config'),
    path('management/<uuid:agent_id>/voice/test/', voice_call_integration.test_agent_voice, name='test-agent-voice'),
    
    # Twilio Call Configuration URLs
    path('management/<uuid:agent_id>/calling/', voice_call_integration.twilio_call_configuration, name='twilio-call-config'),
    path('management/<uuid:agent_id>/calling/test/', voice_call_integration.test_agent_call, name='test-agent-call'),
    
    # Campaign Management URLs
    path('management/contacts/upload/', agent_management_views.upload_contacts, name='upload-contacts'),
    path('management/campaigns/', agent_management_views.campaign_list, name='campaign-list'),
    path('management/campaigns/schedule/', agent_management_views.schedule_campaign, name='schedule-campaign'),
    path('management/campaigns/start-ai/', voice_call_integration.start_campaign_with_ai_voice, name='start-ai-campaign'),
    path('management/queue/status/', agent_management_views.call_queue_status, name='call-queue-status'),
]
