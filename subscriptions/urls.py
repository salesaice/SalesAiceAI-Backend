from django.urls import path
from .admin_package_management import AdminPackageManagementAPIView, AdminIndividualPackageAPIView
from .user_subscription_api import (
    UserPackageSelectionAPIView,
    UserSubscriptionManagementAPIView,
    UserBillingPortalAPIView,
    UserInvoiceManagementAPIView,
    UserSubscribeAPIView,
    AdminStatisticsAPIView
)
# from .first_login_api import UserFirstLoginPackageSelectionAPIView
from .stripe_integration import StripeWebhookAPIView
from .usage_alerts_api import (
    UserUsageAlertsAPIView,
    PlanFeatureAccessAPIView
)
from .payment_methods_api import PaymentMethodsAPIView, PaymentMethodDetailAPIView
from .simple_plans_api import UserPlansComparisonAPIView
from .billing_data_api import BillingDataAPIView

# 🎯 Clean and organized subscription URLs based on image requirements
# Meaningful names, organized by user type, focused on essential functionality

urlpatterns = [
    # 🔐 PACKAGE MANAGEMENT - GET is public, POST/PUT/DELETE require admin
    # Anyone can view packages, only admins can manage them
    path('admin/packages/', AdminPackageManagementAPIView.as_view(), name='admin-packages'),
    path('admin/packages/<uuid:package_id>/', AdminIndividualPackageAPIView.as_view(), name='admin-package-detail'),
    path('admin/statistics/', AdminStatisticsAPIView.as_view(), name='admin-statistics'),
    
    # 👤 USER APIS - Package Selection & Subscription Management
    # Users browse available packages and manage their subscriptions
    # path('user/first-login/', UserFirstLoginPackageSelectionAPIView.as_view(), name='user-first-login'),
    path('user/packages/', UserPackageSelectionAPIView.as_view(), name='user-packages'),
    path('user/subscribe/', UserSubscribeAPIView.as_view(), name='user-subscribe'),
    path('user/subscription/', UserSubscriptionManagementAPIView.as_view(), name='user-subscription'),
    path('user/billing-portal/', UserBillingPortalAPIView.as_view(), name='user-billing-portal'),
    path('user/invoices/', UserInvoiceManagementAPIView.as_view(), name='user-invoices'),
    
    # 📊 USAGE & ALERTS - Monitor usage and plan restrictions
    path('user/usage-alerts/', UserUsageAlertsAPIView.as_view(), name='user-usage-alerts'),
    path('user/feature-access/', PlanFeatureAccessAPIView.as_view(), name='user-feature-access'),
    
    # 💳 PAYMENT METHODS MANAGEMENT - List, add, update, remove payment methods
    path('api/payment-methods/', PaymentMethodsAPIView.as_view(), name='payment-methods'),
    path('api/payment-methods/Detail/', PaymentMethodDetailAPIView.as_view(), name='payment-method-detail'),
    
    # 💳 STRIPE INTEGRATION
    # Webhook for handling Stripe events (payment success/failure, subscription updates)
    path('webhook/stripe/', StripeWebhookAPIView.as_view(), name='stripe-webhook'),

    # 📊 NEW - Simple Plans Comparison API (matches TypeScript interface)
    path('user/plans-comparison/', UserPlansComparisonAPIView.as_view(), name='user-plans-comparison'),
    
    # 💰 NEW - Complete Billing Data API (matches BillingData interface)
    path('user/billing-data/', BillingDataAPIView.as_view(), name='user-billing-data'),
]
