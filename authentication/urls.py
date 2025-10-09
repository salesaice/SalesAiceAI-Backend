from django.urls import path
from . import views
from .api_views import ChangePasswordAPIView
from .quick_auth import QuickTokenAPIView, AdminTokenAPIView, get_all_users_with_tokens

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', ChangePasswordAPIView.as_view(), name='change-password'),
    path('password-reset/', views.password_reset_view, name='password-reset'),
    path('password-reset-confirm/', views.password_reset_confirm_view, name='password-reset-confirm'),
    path('user-email-exist/', views.check_user_Email_exists_view, name='user-email-exist'),
    path('user-name-exist/', views.check_user_name_exists_view, name='user-name-exist'),
    
    # Quick token generation for API testing
    path('quick-token/', QuickTokenAPIView.as_view(), name='quick-token'),
    path('admin-token/', AdminTokenAPIView.as_view(), name='admin-token'),
    path('debug-users/', get_all_users_with_tokens, name='debug-users'),
]
