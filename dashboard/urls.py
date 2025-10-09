from django.urls import path
from .admin_dashboard_api import AdminDashboardAPIView
from .user_dashboard_enhanced import UserDashboardAPIView
from .comprehensive_dashboard import ComprehensiveDashboardAPIView

# CLEAN Dashboard URLs - Essential Only
urlpatterns = [
    # 1. USER DASHBOARD - Main user interface
    path('user/enhanced/', UserDashboardAPIView.as_view(), name='user-dashboard-enhanced'),
    
    # 2. ADMIN DASHBOARD - Admin metrics & management  
    path('admin/dashboard/', AdminDashboardAPIView.as_view(), name='admin-dashboard-api'),
    
    # 3. COMPREHENSIVE DASHBOARD - All data in one API
    path('comprehensive/', ComprehensiveDashboardAPIView.as_view(), name='comprehensive-dashboard'),
]

# Note: AI Agent endpoints moved to agents/urls.py
# Note: SUBSCRIPTION & BILLING handled in subscriptions/urls.py  
# Note: USER ROLES handled in accounts/urls.py
