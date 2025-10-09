from django.urls import path
from . import views_new

app_name = 'agents'

urlpatterns = [
    # Agent List Page (User)
    path('', views_new.agent_list_page, name='agent-list'),
    
    # Create/Edit Agent
    path('create/', views_new.create_edit_agent, name='create-agent'),
    path('edit/', views_new.create_edit_agent, name='edit-agent'),
    
    # Agent Settings and Management
    path('<uuid:agent_id>/settings/', views_new.agent_settings, name='agent-settings'),
    path('<uuid:agent_id>/delete/', views_new.delete_agent, name='delete-agent'),
    
    # Business Knowledge Section
    path('<uuid:agent_id>/knowledge/', views_new.business_knowledge, name='business-knowledge'),
    
    # For Outbound Agents Only
    path('<uuid:agent_id>/contacts/upload/', views_new.upload_contacts, name='upload-contacts'),
    path('<uuid:agent_id>/campaign/schedule/', views_new.schedule_campaign, name='schedule-campaign'),
    path('<uuid:agent_id>/queue/status/', views_new.call_queue_status, name='call-queue-status'),
    
    # Agent Performance
    path('<uuid:agent_id>/performance/', views_new.agent_performance, name='agent-performance'),
]

# Additional API endpoints that might be needed
api_urlpatterns = [
    # Bulk operations
    path('api/agents/bulk-delete/', views_new.bulk_delete_agents, name='api-bulk-delete-agents'),
    path('api/agents/bulk-status/', views_new.bulk_update_status, name='api-bulk-update-status'),
    
    # Campaign management
    path('api/campaigns/', views_new.list_campaigns, name='api-list-campaigns'),
    path('api/campaigns/<uuid:campaign_id>/', views_new.campaign_detail, name='api-campaign-detail'),
    path('api/campaigns/<uuid:campaign_id>/start/', views_new.start_campaign, name='api-start-campaign'),
    path('api/campaigns/<uuid:campaign_id>/pause/', views_new.pause_campaign, name='api-pause-campaign'),
    path('api/campaigns/<uuid:campaign_id>/stop/', views_new.stop_campaign, name='api-stop-campaign'),
    
    # Contact management
    path('api/agents/<uuid:agent_id>/contacts/', views_new.list_contacts, name='api-list-contacts'),
    path('api/contacts/<uuid:contact_id>/', views_new.contact_detail, name='api-contact-detail'),
    
    # Business knowledge management
    path('api/knowledge/<uuid:knowledge_id>/', views_new.knowledge_detail, name='api-knowledge-detail'),
    
    # Performance and analytics
    path('api/agents/<uuid:agent_id>/analytics/', views_new.agent_analytics, name='api-agent-analytics'),
    path('api/dashboard/summary/', views_new.dashboard_summary, name='api-dashboard-summary'),
]

# Combine main URLs with API URLs
urlpatterns += api_urlpatterns