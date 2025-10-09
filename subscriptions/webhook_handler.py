"""
Stripe Webhook Handler for Dynamic Subscription Updates
"""
import json
import logging
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
import stripe

# Generic exception handling for all Stripe versions
StripeError = Exception
SignatureVerificationError = Exception

from subscriptions.models import Subscription

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Handle Stripe webhooks for automatic subscription status updates
    """
    
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        
        if not endpoint_secret:
            logger.error("Stripe webhook secret not configured")
            return HttpResponseBadRequest("Webhook secret not configured")
        
        event = None
        
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return HttpResponseBadRequest("Invalid payload")
        except SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return HttpResponseBadRequest("Invalid signature")
        
        # Handle the event
        try:
            if event['type'] == 'payment_intent.succeeded':
                self.handle_payment_succeeded(event['data']['object'])
            
            elif event['type'] == 'invoice.payment_succeeded':
                self.handle_invoice_payment_succeeded(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.updated':
                self.handle_subscription_updated(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.deleted':
                self.handle_subscription_deleted(event['data']['object'])
            
            elif event['type'] == 'invoice.payment_failed':
                self.handle_payment_failed(event['data']['object'])
            
            else:
                logger.info(f"Unhandled event type: {event['type']}")
            
            return HttpResponse(status=200)
        
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return HttpResponseBadRequest(f"Error handling webhook: {str(e)}")
    
    def handle_payment_succeeded(self, payment_intent):
        """Handle successful payment - activate subscription"""
        try:
            # Get subscription from payment intent
            if payment_intent.get('invoice'):
                invoice = stripe.Invoice.retrieve(payment_intent['invoice'])
                if invoice.subscription:
                    subscription_id = invoice.subscription
                    self.activate_subscription(subscription_id)
            
            logger.info(f"Payment succeeded: {payment_intent['id']}")
        except Exception as e:
            logger.error(f"Error handling payment succeeded: {str(e)}")
    
    def handle_invoice_payment_succeeded(self, invoice):
        """Handle successful invoice payment"""
        try:
            if invoice.get('subscription'):
                subscription_id = invoice['subscription']
                self.activate_subscription(subscription_id)
            
            logger.info(f"Invoice payment succeeded: {invoice['id']}")
        except Exception as e:
            logger.error(f"Error handling invoice payment: {str(e)}")
    
    def handle_subscription_updated(self, subscription):
        """Handle subscription status updates"""
        try:
            subscription_id = subscription['id']
            status = subscription['status']
            
            # Update local subscription
            local_sub = Subscription.objects.filter(
                stripe_subscription_id=subscription_id
            ).first()
            
            if local_sub:
                old_status = local_sub.status
                local_sub.status = self.map_stripe_status(status)
                
                # Update period dates
                if subscription.get('current_period_start'):
                    local_sub.current_period_start = datetime.fromtimestamp(
                        subscription['current_period_start'], tz=dt_timezone.utc
                    )
                
                if subscription.get('current_period_end'):
                    local_sub.current_period_end = datetime.fromtimestamp(
                        subscription['current_period_end'], tz=dt_timezone.utc
                    )
                
                # Handle cancellation
                if subscription.get('canceled_at'):
                    local_sub.canceled_at = datetime.fromtimestamp(
                        subscription['canceled_at'], tz=dt_timezone.utc
                    )
                
                local_sub.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
                local_sub.save()
                
                logger.info(f"Updated subscription {subscription_id}: {old_status} -> {local_sub.status}")
            
        except Exception as e:
            logger.error(f"Error handling subscription update: {str(e)}")
    
    def handle_subscription_deleted(self, subscription):
        """Handle subscription deletion"""
        try:
            subscription_id = subscription['id']
            
            local_sub = Subscription.objects.filter(
                stripe_subscription_id=subscription_id
            ).first()
            
            if local_sub:
                local_sub.status = 'canceled'
                local_sub.canceled_at = timezone.now()
                local_sub.save()
                
                logger.info(f"Canceled subscription: {subscription_id}")
        
        except Exception as e:
            logger.error(f"Error handling subscription deletion: {str(e)}")
    
    def handle_payment_failed(self, invoice):
        """Handle failed payment"""
        try:
            if invoice.get('subscription'):
                subscription_id = invoice['subscription']
                
                local_sub = Subscription.objects.filter(
                    stripe_subscription_id=subscription_id
                ).first()
                
                if local_sub:
                    local_sub.status = 'past_due'
                    local_sub.payment_failed_attempts += 1
                    local_sub.save()
                    
                    logger.info(f"Payment failed for subscription: {subscription_id}")
        
        except Exception as e:
            logger.error(f"Error handling payment failure: {str(e)}")
    
    def activate_subscription(self, subscription_id):
        """Activate a subscription after successful payment"""
        try:
            local_sub = Subscription.objects.filter(
                stripe_subscription_id=subscription_id
            ).first()
            
            if local_sub and local_sub.status == 'pending':
                # Get updated subscription data from Stripe
                stripe_sub = stripe.Subscription.retrieve(subscription_id)
                
                local_sub.status = 'active'
                local_sub.current_period_start = datetime.fromtimestamp(
                    stripe_sub.current_period_start, tz=dt_timezone.utc
                )
                local_sub.current_period_end = datetime.fromtimestamp(
                    stripe_sub.current_period_end, tz=dt_timezone.utc
                )
                local_sub.save()
                
                logger.info(f"Activated subscription: {subscription_id} for user: {local_sub.user.email}")
                return True
        
        except Exception as e:
            logger.error(f"Error activating subscription: {str(e)}")
            return False
    
    def map_stripe_status(self, stripe_status):
        """Map Stripe status to local status"""
        status_mapping = {
            'active': 'active',
            'past_due': 'past_due',
            'canceled': 'canceled',
            'unpaid': 'unpaid',
            'incomplete': 'pending',
            'incomplete_expired': 'expired',
            'trialing': 'trialing',
        }
        return status_mapping.get(stripe_status, stripe_status)
    
    def sync_payment_methods_to_local_db(self, customer_id, user=None):
        """Sync Stripe payment methods to local database"""
        try:
            if not user:
                # Find user by customer ID
                from subscriptions.models import Subscription
                subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
                if subscription:
                    user = subscription.user
                else:
                    logger.warning(f"No user found for customer: {customer_id}")
                    return
            
            # Fetch payment methods from Stripe
            stripe_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type='card'
            )
            
            # Get customer's default payment method
            customer = stripe.Customer.retrieve(customer_id)
            default_pm_id = None
            if hasattr(customer, 'invoice_settings') and customer.invoice_settings:
                if hasattr(customer.invoice_settings, 'default_payment_method'):
                    default_pm_id = customer.invoice_settings.default_payment_method
            
            from subscriptions.models import PaymentMethod
            
            # Sync each payment method
            for stripe_pm in stripe_methods.data:
                try:
                    local_pm, created = PaymentMethod.objects.get_or_create(
                        user=user,
                        stripe_payment_method_id=stripe_pm.id,
                        defaults={
                            'card_type': getattr(stripe_pm.card, 'brand', 'unknown') if stripe_pm.card else 'unknown',
                            'last_four': getattr(stripe_pm.card, 'last4', '0000') if stripe_pm.card else '0000',
                            'exp_month': getattr(stripe_pm.card, 'exp_month', 1) if stripe_pm.card else 1,
                            'exp_year': getattr(stripe_pm.card, 'exp_year', 2030) if stripe_pm.card else 2030,
                            'is_default': stripe_pm.id == default_pm_id,
                            'is_active': True,
                        }
                    )
                    
                    if not created:
                        # Update existing record
                        local_pm.is_default = stripe_pm.id == default_pm_id
                        local_pm.is_active = True
                        local_pm.save()
                    
                    logger.info(f"{'Created' if created else 'Updated'} payment method: {stripe_pm.id}")
                    
                except Exception as pm_error:
                    logger.error(f"Error syncing payment method {stripe_pm.id}: {str(pm_error)}")
            
            logger.info(f"Synced {len(stripe_methods.data)} payment methods for user: {user.email}")
            
        except Exception as e:
            logger.error(f"Error syncing payment methods: {str(e)}")
