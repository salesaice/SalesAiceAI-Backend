from django.urls import path
from .admin_dashboard_api import AdminDashboardAPIView
from .user_dashboard_enhanced import UserDashboardAPIView
from .ai_agent_dashboard import (
    AIAgentDashboardAPIView,
    CustomerProfilesAPIView,
    ScheduledCallbacksAPIView
)

# صرف 4 modules کے لیے required URLs
urlpatterns = [
    # 1. USER DASHBOARD - Main user interface
    path('user/enhanced/', UserDashboardAPIView.as_view(), name='user-dashboard-enhanced'),
    
    # 2. ADMIN DASHBOARD - Admin metrics & management  
    path('admin/dashboard/', AdminDashboardAPIView.as_view(), name='admin-dashboard-api'),
    
    # 3. AI AGENT DASHBOARD - Agent management & monitoring
    # path('ai-agent/', AIAgentDashboardAPIView.as_view(), name='ai-agent-dashboard'),
    # path('ai-agent/customers/', CustomerProfilesAPIView.as_view(), name='ai-agent-customers'),
    # path('ai-agent/callbacks/', ScheduledCallbacksAPIView.as_view(), name='ai-agent-callbacks'),
    
    # 4. SUBSCRIPTION & BILLING - User subscription management (handled in subscriptions/urls.py)
    # 5. USER ROLES - User role management (handled in accounts/urls.py)
]
