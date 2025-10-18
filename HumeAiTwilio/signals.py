"""
Django signals for HumeAI + Twilio Integration
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import TwilioCall, CallAnalytics
from .services import AnalyticsService

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TwilioCall)
def call_status_changed(sender, instance, created, **kwargs):
    """
    Signal handler for when call status changes
    """
    if not created:
        # If call is completed, generate analytics
        if instance.status == 'completed':
            try:
                # Check if analytics already exists
                if not hasattr(instance, 'analytics'):
                    AnalyticsService.calculate_analytics(instance)
                    logger.info(f"Analytics generated for call: {instance.call_sid}")
            except Exception as e:
                logger.error(f"Error generating analytics: {str(e)}")
