from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.conf import settings
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import stripe
import json
import logging

from .models import Subscription, BillingHistory

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookAPIView(APIView):
    """
    Stripe Webhook Handler - Handle Stripe events for subscription management
    """
    
    @swagger_auto_schema(
        tags=['Stripe Integration'],
        operation_summary="Stripe Webhook",
        operation_description="Handle Stripe webhook events for subscription updates",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Stripe webhook payload"
        ),
        responses={
            200: "Webhook processed successfully",
            400: "Invalid webhook signature or payload"
        }
    )
    def post(self, request):
        """Handle Stripe webhook events"""
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            logger.error("Invalid payload in Stripe webhook")
            return HttpResponse("Invalid payload", status=400)
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in Stripe webhook")
            return HttpResponse("Invalid signature", status=400)
        
        # Handle the event
        try:
            if event['type'] == 'customer.subscription.created':
                self._handle_subscription_created(event['data']['object'])
                
            elif event['type'] == 'customer.subscription.updated':
                self._handle_subscription_updated(event['data']['object'])
                
            elif event['type'] == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event['data']['object'])
                
            elif event['type'] == 'invoice.payment_succeeded':
                self._handle_payment_succeeded(event['data']['object'])
                
            elif event['type'] == 'invoice.payment_failed':
                self._handle_payment_failed(event['data']['object'])
                
            else:
                logger.info(f"Unhandled Stripe event type: {event['type']}")
                
        except Exception as e:
            logger.error(f"Error processing Stripe webhook: {str(e)}")
            return HttpResponse("Error processing webhook", status=500)
        
        return HttpResponse("Webhook processed successfully", status=200)
    
    def _handle_subscription_created(self, stripe_subscription):
        """Handle subscription creation"""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription['id']
            )
            subscription.status = 'active'
            subscription.current_period_start = stripe_subscription['current_period_start']
            subscription.current_period_end = stripe_subscription['current_period_end']
            subscription.save()
            
            logger.info(f"Subscription activated: {subscription.id}")
            
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found for Stripe ID: {stripe_subscription['id']}")
    
    def _handle_subscription_updated(self, stripe_subscription):
        """Handle subscription updates"""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription['id']
            )
            
            # Update subscription status
            subscription.status = stripe_subscription['status']
            subscription.current_period_start = stripe_subscription['current_period_start']
            subscription.current_period_end = stripe_subscription['current_period_end']
            subscription.cancel_at_period_end = stripe_subscription.get('cancel_at_period_end', False)
            
            if stripe_subscription.get('canceled_at'):
                subscription.canceled_at = stripe_subscription['canceled_at']
            
            subscription.save()
            
            logger.info(f"Subscription updated: {subscription.id} - Status: {subscription.status}")
            
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found for Stripe ID: {stripe_subscription['id']}")
    
    def _handle_subscription_deleted(self, stripe_subscription):
        """Handle subscription cancellation"""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription['id']
            )
            subscription.status = 'cancelled'
            subscription.canceled_at = stripe_subscription.get('canceled_at')
            subscription.save()
            
            logger.info(f"Subscription cancelled: {subscription.id}")
            
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found for Stripe ID: {stripe_subscription['id']}")
    
    def _handle_payment_succeeded(self, stripe_invoice):
        """Handle successful payment"""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_invoice['subscription']
            )
            
            # Create billing history record
            BillingHistory.objects.create(
                subscription=subscription,
                stripe_invoice_id=stripe_invoice['id'],
                amount=stripe_invoice['amount_paid'] / 100,  # Convert from cents
                currency=stripe_invoice['currency'],
                status='paid',
                description=f"Payment for {subscription.plan.name}",
                invoice_pdf=stripe_invoice.get('invoice_pdf'),
            )
            
            # Reset monthly usage if new billing period
            if subscription.current_period_start != stripe_invoice['period_start']:
                subscription.minutes_used_this_month = 0
                subscription.current_period_start = stripe_invoice['period_start']
                subscription.current_period_end = stripe_invoice['period_end']
                subscription.save()
            
            logger.info(f"Payment succeeded for subscription: {subscription.id}")
            
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found for Stripe subscription ID: {stripe_invoice['subscription']}")
    
    def _handle_payment_failed(self, stripe_invoice):
        """Handle failed payment"""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_invoice['subscription']
            )
            
            # Create billing history record for failed payment
            BillingHistory.objects.create(
                subscription=subscription,
                stripe_invoice_id=stripe_invoice['id'],
                amount=stripe_invoice['amount_due'] / 100,  # Convert from cents
                currency=stripe_invoice['currency'],
                status='failed',
                description=f"Failed payment for {subscription.plan.name}",
            )
            
            # Update subscription status
            subscription.payment_failed_attempts += 1
            subscription.save()
            
            logger.warning(f"Payment failed for subscription: {subscription.id}")
            
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found for Stripe subscription ID: {stripe_invoice['subscription']}")
