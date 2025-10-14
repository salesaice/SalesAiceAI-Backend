from django.urls import path
from . import views
from . import ai_training_views
from . import ai_conversation_system
from . import views_call_routing

app_name = 'agents'

# CORE AGENT ENDPOINTS ONLY - Minimal & Essential
urlpatterns = [
    # 1. Basic Agent CRUD
    path('', views.agent_list_page, name='agent-list'),                           # GET /agents/
    path('<uuid:agent_id>/', views.agent_detail, name='agent-detail'),           # GET /agents/{agent_id}/
    path('create/', views.create_agent, name='create-agent'),                   # POST /agents/create/
    path('<uuid:agent_id>/update/', views.update_agent, name='update-agent'),   # PUT /agents/{agent_id}/update/
    path('<uuid:agent_id>/delete/', views.delete_agent, name='delete-agent'),   # DELETE /agents/{agent_id}/delete/
    
    # AI AGENT SYSTEM - NEW ENDPOINTS
    path('ai/training/', ai_training_views.ai_agent_training, name='ai-training'),                    # GET/POST /agents/ai/training/
    path('ai/learning/', ai_training_views.ai_agent_learning, name='ai-learning'),                    # POST /agents/ai/learning/
    path('ai/response/', ai_training_views.ai_agent_response_generator, name='ai-response'),          # POST /agents/ai/response/
    path('ai/start-call/', ai_conversation_system.start_ai_call, name='ai-start-call'),               # POST /agents/ai/start-call/
    path('ai/complete-call/', ai_conversation_system.complete_ai_call, name='ai-complete-call'),      # POST /agents/ai/complete-call/
    
    # WEBHOOKS - External Integration
    path('webhooks/hume-ai/', ai_conversation_system.hume_ai_webhook, name='hume-webhook'),           # POST /agents/webhooks/hume-ai/
    path('webhooks/twilio/', ai_conversation_system.twilio_voice_webhook, name='twilio-webhook'),     # POST /agents/webhooks/twilio/
    
    # 2. Agent Features
    path('<uuid:agent_id>/analytics/', views.agent_analytics, name='agent-analytics'),        # GET /agents/{agent_id}/analytics/
    path('<uuid:agent_id>/contacts/', views.agent_contacts, name='agent-contacts'),           # GET/POST /agents/{agent_id}/contacts/
    path('<uuid:agent_id>/knowledge/', views.agent_knowledge, name='agent-knowledge'),        # GET/POST /agents/{agent_id}/knowledge/
    
    # 3. Campaign Management (Outbound Agents)
    path('campaigns/', views.campaigns_list, name='campaigns-list'),                          # GET /agents/campaigns/
    path('campaigns/<uuid:campaign_id>/', views.campaign_detail, name='campaign-detail'),     # GET/PUT /agents/campaigns/{campaign_id}/
    path('<uuid:agent_id>/campaigns/create/', views.create_campaign, name='create-campaign'), # POST /agents/{agent_id}/campaigns/create/
    
    # 4. Call Queue Management (Outbound Agents)
    path('<uuid:agent_id>/call-queue/', views.call_queue, name='call-queue'),                 # GET /agents/{agent_id}/call-queue/
    
    # 5. Enhanced Delete (with validation)
    path('<uuid:agent_id>/delete-enhanced/', views.delete_agent_enhanced, name='delete-agent-enhanced'), # DELETE /agents/{agent_id}/delete-enhanced/
    
    # 6. Bulk Operations
    path('bulk-delete/', views.bulk_delete_agents, name='bulk-delete-agents'),               # POST /agents/bulk-delete/
    path('bulk-status/', views.bulk_status_update, name='bulk-status-update'),               # POST /agents/bulk-status/
    
    # 5. Knowledge Management
    path('knowledge/<uuid:knowledge_id>/', views.knowledge_detail, name='knowledge-detail'), # GET/PUT/DELETE /agents/knowledge/{knowledge_id}/
    
    # 6. Dashboard  
    path('dashboard/summary/', views.dashboard_summary, name='dashboard-summary'),            # GET /agents/dashboard/summary/
    
    # 7. Call Routing (Inbound Agents)
    path('call-routing/test/', views_call_routing.CallRoutingTestView.as_view(), name='call-routing-test'),         # POST /agents/call-routing/test/
    path('call-routing/stats/', views_call_routing.CallRoutingStatsView.as_view(), name='call-routing-stats'),      # GET /agents/call-routing/stats/
    path('call-routing/available/', views_call_routing.AvailableAgentsView.as_view(), name='available-agents'),     # GET /agents/call-routing/available/
    path('call-routing/simulate/', views_call_routing.SimulateInboundCallView.as_view(), name='simulate-inbound'),  # POST /agents/call-routing/simulate/
    
    # 8. Agent Status API (Frontend Interface)
    path('status/', views.agent_status_list, name='agent-status-list'),                      # GET /agents/status/
    
    # 9. Outbound Agents API (Simple & Fast)
    path('outbound/', views.outbound_agents_list, name='outbound-agents-list'),               # GET /agents/outbound/
]