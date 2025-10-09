import stripe
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Subscription, SubscriptionPlan, BillingHistory, PaymentMethod, UsageAlert

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Complete Stripe integration service"""
    
    @staticmethod
    def create_customer(user):
        """Create Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
                metadata={
                    'user_id': str(user.id),
                    'created_from': 'django_app'
                }
            )
            
            logger.info(f"Created Stripe customer: {customer.id} for user: {user.email}")
            return customer
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            return None
    
    @staticmethod
    def create_payment_intent(amount, currency='usd', customer_id=None, metadata=None):
        """Create payment intent for one-time payments"""
        try:
            payment_intent_data = {
                'amount': int(amount * 100),  # Convert to cents
                'currency': currency,
                'automatic_payment_methods': {'enabled': True},
            }
            
            if customer_id:
                payment_intent_data['customer'] = customer_id
            
            if metadata:
                payment_intent_data['metadata'] = metadata
            
            payment_intent = stripe.PaymentIntent.create(**payment_intent_data)
            
            logger.info(f"Created payment intent: {payment_intent.id}")
            return payment_intent
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            return None
    
    @staticmethod
    def create_subscription(customer_id, price_id, trial_days=None, metadata=None):
        """Create Stripe subscription"""
        try:
            subscription_data = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'payment_settings': {'save_default_payment_method': 'on_subscription'},
                'expand': ['latest_invoice.payment_intent'],
            }
            
            if trial_days:
                subscription_data['trial_period_days'] = trial_days
            
            if metadata:
                subscription_data['metadata'] = metadata
            
            subscription = stripe.Subscription.create(**subscription_data)
            
            logger.info(f"Created Stripe subscription: {subscription.id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {str(e)}")
            return None
    
    @staticmethod
    def update_subscription(subscription_id, **kwargs):
        """Update Stripe subscription"""
        try:
            subscription = stripe.Subscription.modify(subscription_id, **kwargs)
            logger.info(f"Updated Stripe subscription: {subscription_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error updating subscription: {str(e)}")
            return None
    
    @staticmethod
    def cancel_subscription(subscription_id, at_period_end=True):
        """Cancel Stripe subscription"""
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Canceled Stripe subscription: {subscription_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {str(e)}")
            return None
    
    @staticmethod
    def attach_payment_method(payment_method_id, customer_id):
        """Attach payment method to customer"""
        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            
            logger.info(f"Attached payment method: {payment_method_id} to customer: {customer_id}")
            return payment_method
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error attaching payment method: {str(e)}")
            return None
    
    @staticmethod
    def detach_payment_method(payment_method_id):
        """Detach payment method"""
        try:
            payment_method = stripe.PaymentMethod.detach(payment_method_id)
            logger.info(f"Detached payment method: {payment_method_id}")
            return payment_method
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error detaching payment method: {str(e)}")
            return None
    
    @staticmethod
    def set_default_payment_method(customer_id, payment_method_id):
        """Set default payment method for customer"""
        try:
            customer = stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
            
            logger.info(f"Set default payment method: {payment_method_id} for customer: {customer_id}")
            return customer
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error setting default payment method: {str(e)}")
            return None
    
    @staticmethod
    def retrieve_customer(customer_id):
        """Retrieve Stripe customer"""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving customer: {str(e)}")
            return None
    
    @staticmethod
    def list_payment_methods(customer_id, type='card'):
        """List customer payment methods"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=type
            )
            return payment_methods
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error listing payment methods: {str(e)}")
            return None
    
    @staticmethod
    def retrieve_invoice(invoice_id):
        """Retrieve Stripe invoice"""
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return invoice
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving invoice: {str(e)}")
            return None
    
    @staticmethod
    def create_portal_session(customer_id, return_url):
        """Create customer portal session"""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )
            
            logger.info(f"Created portal session for customer: {customer_id}")
            return session
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {str(e)}")
            return None


class BillingService:
    """Billing and subscription management service"""
    
    @staticmethod
    def create_subscription_for_user(user, plan, payment_method_id=None, trial_days=None):
        """Create complete subscription for user"""
        try:
            # Create or get Stripe customer
            if hasattr(user, 'subscription') and user.subscription.stripe_customer_id:
                customer_id = user.subscription.stripe_customer_id
            else:
                stripe_customer = StripeService.create_customer(user)
                if not stripe_customer:
                    return {'success': False, 'error': 'Failed to create customer'}
                customer_id = stripe_customer.id
            
            # Attach payment method if provided
            if payment_method_id:
                StripeService.attach_payment_method(payment_method_id, customer_id)
                StripeService.set_default_payment_method(customer_id, payment_method_id)
            
            # Create Stripe subscription
            trial_period = trial_days or (14 if plan.plan_type == 'starter' else 7)
            
            stripe_subscription = StripeService.create_subscription(
                customer_id=customer_id,
                price_id=plan.stripe_price_id,
                trial_days=trial_period,
                metadata={
                    'user_id': str(user.id),
                    'plan_id': str(plan.id),
                    'plan_name': plan.name
                }
            )
            
            if not stripe_subscription:
                return {'success': False, 'error': 'Failed to create subscription'}
            
            # Create or update local subscription
            trial_end = timezone.now() + timedelta(days=trial_period)
            period_end = trial_end + timedelta(days=30 if plan.billing_cycle == 'month' else 365)
            
            subscription, created = Subscription.objects.get_or_create(
                user=user,
                defaults={
                    'plan': plan,
                    'status': stripe_subscription.status,
                    'stripe_subscription_id': stripe_subscription.id,
                    'stripe_customer_id': customer_id,
                    'stripe_payment_method_id': payment_method_id,
                    'current_period_start': timezone.now(),
                    'current_period_end': period_end,
                    'trial_start': timezone.now(),
                    'trial_end': trial_end,
                }
            )
            
            if not created:
                # Update existing subscription
                subscription.plan = plan
                subscription.status = stripe_subscription.status
                subscription.stripe_subscription_id = stripe_subscription.id
                subscription.stripe_customer_id = customer_id
                subscription.stripe_payment_method_id = payment_method_id
                subscription.trial_end = trial_end
                subscription.current_period_end = period_end
                subscription.save()
            
            # Store payment method info
            if payment_method_id:
                BillingService.store_payment_method(user, payment_method_id)
            
            logger.info(f"Created subscription for user: {user.email}, plan: {plan.name}")
            
            return {
                'success': True,
                'subscription': subscription,
                'stripe_subscription': stripe_subscription,
                'client_secret': stripe_subscription.latest_invoice.payment_intent.client_secret if stripe_subscription.latest_invoice else None
            }
            
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def store_payment_method(user, payment_method_id):
        """Store payment method details"""
        try:
            pm = stripe.PaymentMethod.retrieve(payment_method_id)
            
            # Set all other payment methods as non-default
            PaymentMethod.objects.filter(user=user, is_default=True).update(is_default=False)
            
            # Create or update payment method
            payment_method, created = PaymentMethod.objects.get_or_create(
                user=user,
                stripe_payment_method_id=payment_method_id,
                defaults={
                    'card_type': pm.card.brand,
                    'last_four': pm.card.last4,
                    'exp_month': pm.card.exp_month,
                    'exp_year': pm.card.exp_year,
                    'is_default': True,
                }
            )
            
            return payment_method
            
        except Exception as e:
            logger.error(f"Error storing payment method: {str(e)}")
            return None
    
    @staticmethod
    def update_subscription_plan(subscription, new_plan):
        """Upgrade/downgrade subscription plan"""
        try:
            # Update Stripe subscription
            stripe_subscription = StripeService.update_subscription(
                subscription.stripe_subscription_id,
                items=[{
                    'id': subscription.stripe_subscription_id,
                    'price': new_plan.stripe_price_id,
                }],
                proration_behavior='create_prorations'
            )
            
            if stripe_subscription:
                # Update local subscription
                subscription.plan = new_plan
                subscription.save()
                
                # Create billing history record
                BillingHistory.objects.create(
                    subscription=subscription,
                    invoice_type='subscription',
                    amount=new_plan.price,
                    total_amount=new_plan.price,
                    status='paid',
                    description=f'Plan changed to {new_plan.name}',
                    billing_period_start=timezone.now(),
                    billing_period_end=subscription.current_period_end,
                    due_date=timezone.now(),
                    paid_at=timezone.now()
                )
                
                logger.info(f"Updated subscription plan for user: {subscription.user.email}")
                
                return {'success': True, 'subscription': subscription}
            
            return {'success': False, 'error': 'Failed to update Stripe subscription'}
            
        except Exception as e:
            logger.error(f"Error updating subscription plan: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def cancel_subscription(subscription, at_period_end=True):
        """Cancel user subscription"""
        try:
            # Cancel Stripe subscription
            stripe_subscription = StripeService.cancel_subscription(
                subscription.stripe_subscription_id,
                at_period_end=at_period_end
            )
            
            if stripe_subscription:
                # Update local subscription
                subscription.cancel_at_period_end = at_period_end
                if not at_period_end:
                    subscription.status = 'canceled'
                    subscription.canceled_at = timezone.now()
                subscription.save()
                
                # Create alert
                UsageAlert.objects.create(
                    subscription=subscription,
                    alert_type='subscription_ending',
                    priority='high',
                    title='Subscription Canceled',
                    message='Your subscription has been canceled.',
                    action_required=False
                )
                
                logger.info(f"Canceled subscription for user: {subscription.user.email}")
                
                return {'success': True}
            
            return {'success': False, 'error': 'Failed to cancel Stripe subscription'}
            
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def process_usage_billing(subscription, minutes_used):
        """Process usage and overage billing"""
        try:
            # Update usage
            subscription.update_usage(minutes_used)
            
            # Handle overage charges
            if subscription.overage_charges > 0:
                # Create invoice item for overage
                stripe.InvoiceItem.create(
                    customer=subscription.stripe_customer_id,
                    amount=int(subscription.overage_charges * 100),
                    currency='usd',
                    description=f'Overage charges: {subscription.overage_minutes} minutes'
                )
                
                # Create billing history
                BillingHistory.objects.create(
                    subscription=subscription,
                    invoice_type='overage',
                    amount=subscription.overage_charges,
                    total_amount=subscription.overage_charges,
                    status='pending',
                    description=f'Overage charges for {subscription.overage_minutes} minutes',
                    billing_period_start=subscription.current_period_start,
                    billing_period_end=subscription.current_period_end,
                    due_date=timezone.now() + timedelta(days=7)
                )
                
                logger.info(f"Processed overage billing for user: {subscription.user.email}")
            
            return {'success': True, 'overage_charges': subscription.overage_charges}
            
        except Exception as e:
            logger.error(f"Error processing usage billing: {str(e)}")
            return {'success': False, 'error': str(e)}


class WebhookService:
    """Handle Stripe webhooks"""
    
    @staticmethod
    def handle_webhook_event(event):
        """Process Stripe webhook events"""
        try:
            event_type = event['type']
            data_object = event['data']['object']
            
            if event_type == 'invoice.payment_succeeded':
                return WebhookService._handle_payment_succeeded(data_object)
            elif event_type == 'invoice.payment_failed':
                return WebhookService._handle_payment_failed(data_object)
            elif event_type == 'customer.subscription.updated':
                return WebhookService._handle_subscription_updated(data_object)
            elif event_type == 'customer.subscription.deleted':
                return WebhookService._handle_subscription_deleted(data_object)
            elif event_type == 'customer.subscription.created':
                return WebhookService._handle_subscription_created(data_object)
            elif event_type == 'invoice.created':
                return WebhookService._handle_invoice_created(data_object)
            elif event_type == 'payment_method.attached':
                return WebhookService._handle_payment_method_attached(data_object)
            elif event_type == 'setup_intent.succeeded':
                return WebhookService._handle_setup_intent_succeeded(data_object)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return {'success': True, 'message': 'Event type not handled'}
                
        except Exception as e:
            logger.error(f"Error handling webhook event: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _handle_subscription_created(subscription_data):
        """Handle new subscription creation webhook"""
        try:
            # Get customer from Stripe
            customer = stripe.Customer.retrieve(subscription_data['customer'])
            
            try:
                user = User.objects.get(email=customer['email'])
            except User.DoesNotExist:
                logger.error(f"User not found for subscription creation: {customer['email']}")
                return {'success': False, 'error': 'User not found'}
            
            # Check if subscription already exists
            if Subscription.objects.filter(
                stripe_subscription_id=subscription_data['id']
            ).exists():
                logger.info(f"Subscription already exists: {subscription_data['id']}")
                return {'success': True, 'message': 'Subscription already exists'}
            
            # Get the price ID to find the plan
            price_id = subscription_data['items']['data'][0]['price']['id']
            try:
                plan = SubscriptionPlan.objects.get(stripe_price_id=price_id)
            except SubscriptionPlan.DoesNotExist:
                logger.error(f"Plan not found for price ID: {price_id}")
                return {'success': False, 'error': 'Plan not found'}
            
            # Create subscription
            subscription = Subscription.objects.create(
                user=user,
                plan=plan,
                stripe_subscription_id=subscription_data['id'],
                stripe_customer_id=customer['id'],
                status=subscription_data['status'],
                current_period_start=timezone.datetime.fromtimestamp(
                    subscription_data['current_period_start']
                ),
                current_period_end=timezone.datetime.fromtimestamp(
                    subscription_data['current_period_end']
                ),
                billing_cycle='monthly' if subscription_data.get('items', {}).get('data', [{}])[0].get('price', {}).get('recurring', {}).get('interval') == 'month' else 'yearly'
            )
            
            logger.info(f"Subscription created from webhook: {subscription.id}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error handling subscription creation webhook: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _handle_invoice_created(invoice_data):
        """Handle invoice creation webhook"""
        try:
            if not invoice_data.get('subscription'):
                return {'success': True, 'message': 'Not a subscription invoice'}
            
            subscription = Subscription.objects.get(
                stripe_subscription_id=invoice_data['subscription']
            )
            
            # Create billing history record
            BillingHistory.objects.create(
                user=subscription.user,
                subscription=subscription,
                invoice_type='subscription',
                amount=invoice_data['amount_due'] / 100,
                total_amount=invoice_data['total'] / 100,
                status='pending',
                description=f'Invoice for {subscription.plan.name}',
                stripe_invoice_id=invoice_data['id'],
                billing_period_start=timezone.datetime.fromtimestamp(
                    invoice_data['period_start']
                ),
                billing_period_end=timezone.datetime.fromtimestamp(
                    invoice_data['period_end']
                ),
                due_date=timezone.datetime.fromtimestamp(
                    invoice_data['due_date']
                ) if invoice_data.get('due_date') else timezone.now() + timedelta(days=7),
                invoice_url=invoice_data.get('hosted_invoice_url')
            )
            
            logger.info(f"Invoice created for subscription: {subscription.id}")
            return {'success': True}
            
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found for invoice: {invoice_data['id']}")
            return {'success': False, 'error': 'Subscription not found'}
        except Exception as e:
            logger.error(f"Error handling invoice creation: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _handle_payment_method_attached(payment_method_data):
        """Handle payment method attachment webhook"""
        try:
            customer_id = payment_method_data.get('customer')
            if not customer_id:
                return {'success': True, 'message': 'Payment method not attached to customer'}
            
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
            except User.DoesNotExist:
                logger.error(f"User not found for customer: {customer_id}")
                return {'success': False, 'error': 'User not found'}
            
            # Store payment method
            self.store_payment_method(user, payment_method_data['id'])
            
            logger.info(f"Payment method attached for user: {user.id}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error handling payment method attachment: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _handle_setup_intent_succeeded(setup_intent_data):
        """Handle setup intent success webhook"""
        try:
            customer_id = setup_intent_data.get('customer')
            payment_method_id = setup_intent_data.get('payment_method')
            
            if not customer_id or not payment_method_id:
                return {'success': True, 'message': 'Missing customer or payment method'}
            
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
            except User.DoesNotExist:
                logger.error(f"User not found for customer: {customer_id}")
                return {'success': False, 'error': 'User not found'}
            
            # Store payment method
            self.store_payment_method(user, payment_method_id)
            
            logger.info(f"Setup intent succeeded for user: {user.id}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error handling setup intent success: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_customer_invoices(user, limit=10):
        """Get customer's Stripe invoices"""
        try:
            if not user.stripe_customer_id:
                return []
            
            invoices = stripe.Invoice.list(
                customer=user.stripe_customer_id,
                limit=limit
            )
            
            invoice_data = []
            for invoice in invoices.data:
                invoice_data.append({
                    'id': invoice.id,
                    'amount_paid': invoice.amount_paid / 100,
                    'amount_due': invoice.amount_due / 100,
                    'total': invoice.total / 100,
                    'status': invoice.status,
                    'created': timezone.datetime.fromtimestamp(invoice.created),
                    'due_date': timezone.datetime.fromtimestamp(invoice.due_date) if invoice.due_date else None,
                    'period_start': timezone.datetime.fromtimestamp(invoice.period_start) if invoice.period_start else None,
                    'period_end': timezone.datetime.fromtimestamp(invoice.period_end) if invoice.period_end else None,
                    'invoice_pdf': invoice.invoice_pdf,
                    'hosted_invoice_url': invoice.hosted_invoice_url,
                    'description': invoice.description or f'Subscription invoice'
                })
            
            return invoice_data
            
        except Exception as e:
            logger.error(f"Error fetching customer invoices: {str(e)}")
            return []
    
    @staticmethod
    def get_customer_payment_methods(user):
        """Get customer's payment methods"""
        try:
            if not user.stripe_customer_id:
                return []
            
            payment_methods = stripe.PaymentMethod.list(
                customer=user.stripe_customer_id,
                type='card'
            )
            
            methods_data = []
            for pm in payment_methods.data:
                methods_data.append({
                    'id': pm.id,
                    'brand': pm.card.brand,
                    'last4': pm.card.last4,
                    'exp_month': pm.card.exp_month,
                    'exp_year': pm.card.exp_year,
                    'is_default': pm.id == user.stripe_customer_id  # This would need proper default logic
                })
            
            return methods_data
            
        except Exception as e:
            logger.error(f"Error fetching payment methods: {str(e)}")
            return []
    
    @staticmethod
    def attach_payment_method(user, payment_method_id):
        """Attach payment method to customer"""
        try:
            # Ensure customer exists
            result = BillingService.get_or_create_customer(user)
            if not result['success']:
                return result
            
            # Attach payment method
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.stripe_customer_id
            )
            
            # Store locally
            BillingService.store_payment_method(user, payment_method_id)
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error attaching payment method: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_or_create_customer(user):
        """Get or create Stripe customer for user"""
        try:
            # Check if user already has a Stripe customer ID
            if hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
                try:
                    # Verify customer exists in Stripe
                    customer = stripe.Customer.retrieve(user.stripe_customer_id)
                    return {'success': True, 'customer': customer}
                except stripe.error.InvalidRequestError:
                    # Customer doesn't exist in Stripe, create new one
                    pass
            
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip(),
                metadata={
                    'user_id': str(user.id),
                    'user_email': user.email,
                }
            )
            
            # Save customer ID to user
            user.stripe_customer_id = customer.id
            user.save()
            
            return {'success': True, 'customer': customer}
            
        except Exception as e:
            logger.error(f"Error creating/retrieving customer: {str(e)}")
            return {'success': False, 'error': str(e)}
