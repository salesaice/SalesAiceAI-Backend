from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.CallSessionsAPIView.as_view(), name='call-sessions'),
    path('queue/', views.CallQueueAPIView.as_view(), name='call-queue'),
    path('start-call/', views.StartCallAPIView.as_view(), name='start-call'),
    path('twilio-webhook/', views.TwilioWebhookAPIView.as_view(), name='twilio-webhook'),
    path('ai-assistance/', views.HomeAIIntegrationAPIView.as_view(), name='homeai-assistance'),
    path('quick-actions/', views.QuickActionsAPIView.as_view(), name='quick-actions'),
]
