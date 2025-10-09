from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import uuid
import stripe
from django.conf import settings

User = get_user_model()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionPlan(models.Model):
    """Enhanced subscription packages with Stripe integration"""
    PLAN_TYPES = [
        ('starter', 'Starter'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
        ('custom', 'Custom Enterprise'),
    ]
    
    BILLING_CYCLES = [
        ('month', 'Monthly'),
        ('year', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default='month')
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    setup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.IntegerField(default=0, help_text="Annual discount %")
    
    # Core Features
    call_minutes_limit = models.IntegerField(default=1000, help_text="Monthly call minutes")
    minutes_inbound_limit = models.IntegerField(default=500, help_text="Monthly inbound call minutes")
    minutes_outbound_limit = models.IntegerField(default=500, help_text="Monthly outbound call minutes")
    agents_allowed = models.IntegerField(default=1, help_text="Number of agents allowed")
    ai_agents_allowed = models.IntegerField(default=1, help_text="AI agents allowed")
    concurrent_calls = models.IntegerField(default=5, help_text="Concurrent calls limit")
    
    # Advanced Features
    analytics_access = models.BooleanField(default=False)
    advanced_analytics = models.BooleanField(default=False)
    api_access = models.BooleanField(default=False)
    webhook_access = models.BooleanField(default=False)
    custom_integration = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    
    # Call Center Features
    call_recording = models.BooleanField(default=False)
    call_transcription = models.BooleanField(default=False)
    sentiment_analysis = models.BooleanField(default=False)
    auto_campaigns = models.BooleanField(default=False)
    crm_integration = models.BooleanField(default=False)
    
    # Storage & Backup
    storage_gb = models.IntegerField(default=1, help_text="Storage in GB")
    backup_retention_days = models.IntegerField(default=30)
    
    # Stripe Integration
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Admin
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'price']
    
    def __str__(self):
        return f"{self.name} - ${self.price}/{self.billing_cycle}"
    
    @property
    def yearly_price(self):
        """Calculate yearly price with discount"""
        if self.billing_cycle == 'year':
            return self.price
        elif self.billing_cycle == 'month':
            monthly_yearly = self.price * 12
            discount = monthly_yearly * (self.discount_percentage / 100)
            return monthly_yearly - discount
        return self.price
    
    @property
    def monthly_equivalent(self):
        """Monthly equivalent price"""
        if self.billing_cycle == 'month':
            return self.price
        elif self.billing_cycle == 'year':
            return self.price / 12
        return self.price
    
    @property
    def features(self):
        """Return features in the required structure for frontend"""
        return {
            'campaigns': self.concurrent_calls if self.auto_campaigns else 0,  # number - campaign capacity
            'api_access': self.api_access,  # boolean
            'advanced_analytics': self.advanced_analytics if self.analytics_access else False,  # boolean
        }
    
    def create_stripe_product(self):
        """Create Stripe product and price"""
        try:
            # Create Stripe product
            product = stripe.Product.create(
                name=self.name,
                description=f"{self.name} plan with {self.call_minutes_limit} minutes/month",
                metadata={
                    'plan_id': str(self.id),
                    'plan_type': self.plan_type
                }
            )
            
            # Create Stripe price
            interval = 'month' if self.billing_cycle == 'month' else 'year'
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(self.price * 100),  # Convert to cents
                currency='usd',
                recurring={'interval': interval} if self.billing_cycle != 'lifetime' else None,
                metadata={'plan_id': str(self.id)}
            )
            
            self.stripe_product_id = product.id
            self.stripe_price_id = price.id
            self.save()
            
            return {'success': True, 'product_id': product.id, 'price_id': price.id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


class Subscription(models.Model):
    """Enhanced subscription management with Stripe"""
    STATUS_CHOICES = [
        ('trialing', 'Trial'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('incomplete', 'Incomplete'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    
    # Stripe Integration
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_payment_method_id = models.CharField(max_length=100, blank=True)
    
    # Billing Period
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    # Usage Tracking
    minutes_used_this_month = models.IntegerField(default=0)
    overage_minutes = models.IntegerField(default=0)
    overage_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Auto-renewal and notifications
    auto_renew = models.BooleanField(default=True)
    renewal_notification_sent = models.BooleanField(default=False)
    payment_failed_attempts = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"
    
    @property
    def is_active(self):
        return self.status in ['active', 'trialing'] and self.current_period_end > timezone.now()
    
    @property
    def is_trial(self):
        return self.status == 'trialing' and self.trial_end and self.trial_end > timezone.now()
    
    @property
    def days_remaining(self):
        if self.current_period_end > timezone.now():
            return (self.current_period_end - timezone.now()).days
        return 0
    
    @property
    def trial_days_remaining(self):
        if self.is_trial:
            return (self.trial_end - timezone.now()).days
        return 0
    
    @property
    def minutes_remaining(self):
        return max(0, self.plan.call_minutes_limit - self.minutes_used_this_month)
    
    @property
    def usage_percentage(self):
        if self.plan.call_minutes_limit == 0:
            return 0
        return min(100, (self.minutes_used_this_month / self.plan.call_minutes_limit) * 100)
    
    @property
    def is_usage_warning(self):
        return self.usage_percentage > 80
    
    @property
    def is_usage_exceeded(self):
        return self.minutes_used_this_month > self.plan.call_minutes_limit
    
    def create_stripe_customer(self):
        """Create Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=self.user.email,
                name=f"{self.user.first_name} {self.user.last_name}",
                metadata={
                    'user_id': str(self.user.id),
                    'subscription_id': str(self.id)
                }
            )
            
            self.stripe_customer_id = customer.id
            self.save()
            return customer
            
        except Exception as e:
            return None
    
    def create_stripe_subscription(self, payment_method_id=None):
        """Create Stripe subscription"""
        try:
            if not self.stripe_customer_id:
                self.create_stripe_customer()
            
            subscription_data = {
                'customer': self.stripe_customer_id,
                'items': [{'price': self.plan.stripe_price_id}],
                'metadata': {
                    'subscription_id': str(self.id),
                    'user_id': str(self.user.id)
                }
            }
            
            if payment_method_id:
                subscription_data['default_payment_method'] = payment_method_id
                self.stripe_payment_method_id = payment_method_id
            
            # Add trial period if applicable
            if self.trial_end:
                subscription_data['trial_end'] = int(self.trial_end.timestamp())
            
            stripe_subscription = stripe.Subscription.create(**subscription_data)
            
            self.stripe_subscription_id = stripe_subscription.id
            self.status = stripe_subscription.status
            self.save()
            
            return stripe_subscription
            
        except Exception as e:
            return None
    
    def cancel_subscription(self, at_period_end=True):
        """Cancel Stripe subscription"""
        try:
            if self.stripe_subscription_id:
                stripe.Subscription.modify(
                    self.stripe_subscription_id,
                    cancel_at_period_end=at_period_end
                )
                
                self.cancel_at_period_end = at_period_end
                if not at_period_end:
                    self.status = 'canceled'
                    self.canceled_at = timezone.now()
                self.save()
                
                return True
        except Exception as e:
            return False
    
    def update_usage(self, minutes_used):
        """Update usage and handle overages"""
        self.minutes_used_this_month += minutes_used
        
        # Calculate overage
        if self.minutes_used_this_month > self.plan.call_minutes_limit:
            self.overage_minutes = self.minutes_used_this_month - self.plan.call_minutes_limit
            # $0.02 per overage minute
            self.overage_charges = Decimal(str(self.overage_minutes * 0.02))
        
        self.save()
        
        # Create usage alerts
        if self.usage_percentage > 80 and not self.usage_alerts.filter(alert_type='limit_warning').exists():
            UsageAlert.objects.create(
                subscription=self,
                alert_type='limit_warning',
                message=f"You've used {self.usage_percentage}% of your monthly minutes."
            )
        
        if self.is_usage_exceeded and not self.usage_alerts.filter(alert_type='limit_exceeded').exists():
            UsageAlert.objects.create(
                subscription=self,
                alert_type='limit_exceeded',
                message=f"You've exceeded your monthly limit. Overage charges: ${self.overage_charges}"
            )


class BillingHistory(models.Model):
    """Enhanced payment history and invoices"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    INVOICE_TYPES = [
        ('subscription', 'Subscription'),
        ('overage', 'Overage Charges'),
        ('setup', 'Setup Fee'),
        ('addon', 'Add-on'),
        ('credit', 'Credit'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='billing_history')
    
    # Invoice Details
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPES, default='subscription')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Status and Description
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    description = models.CharField(max_length=255, blank=True)
    
    # Billing Period
    billing_period_start = models.DateTimeField(null=True, blank=True)
    billing_period_end = models.DateTimeField(null=True, blank=True)
    
    # Stripe Integration
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_charge_id = models.CharField(max_length=100, blank=True)
    
    # Payment Details
    payment_method = models.CharField(max_length=50, blank=True)  # card, bank_transfer, etc.
    last_four = models.CharField(max_length=4, blank=True)  # Last 4 digits of card
    
    # Timestamps
    due_date = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subscription.user.email} - ${self.total_amount} - {self.status}"
    
    @property
    def is_overdue(self):
        return self.status == 'pending' and self.due_date < timezone.now()


class PaymentMethod(models.Model):
    """Stored payment methods"""
    CARD_TYPES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    
    # Card Details
    stripe_payment_method_id = models.CharField(max_length=100)
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    last_four = models.CharField(max_length=4)
    exp_month = models.IntegerField()
    exp_year = models.IntegerField()
    
    # Status
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.card_type} **** {self.last_four}"


class UsageAlert(models.Model):
    """Enhanced usage alerts and notifications"""
    ALERT_TYPES = [
        ('limit_warning', 'Usage Warning (80%)'),
        ('limit_exceeded', 'Limit Exceeded'),
        ('payment_failed', 'Payment Failed'),
        ('subscription_ending', 'Subscription Ending'),
        ('trial_ending', 'Trial Ending'),
        ('overage_charges', 'Overage Charges'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='usage_alerts')
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    title = models.CharField(max_length=200, default='Alert')
    message = models.TextField()
    
    # Actions
    action_required = models.BooleanField(default=False)
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Notifications
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subscription.user.email} - {self.title}"
    
    def mark_resolved(self):
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save()


class UsageRecord(models.Model):
    """Track usage for billing and limits"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='usage_records')
    
    # Usage data
    minutes_used = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    agents_used = models.IntegerField(default=0)
    storage_used_mb = models.IntegerField(default=0)
    api_calls_made = models.IntegerField(default=0)
    
    # Metadata
    call_id = models.CharField(max_length=100, blank=True, null=True)
    agent_id = models.CharField(max_length=100, blank=True, null=True)
    feature_used = models.CharField(max_length=100, blank=True, null=True)
    metadata = models.JSONField(default=dict)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['subscription', 'timestamp']),
            models.Index(fields=['call_id']),
        ]
    
    def __str__(self):
        return f"{self.subscription.user.email} - {self.minutes_used} mins - {self.timestamp}"


class SubscriptionAddon(models.Model):
    """Additional features/add-ons"""
    ADDON_TYPES = [
        ('minutes', 'Extra Minutes'),
        ('storage', 'Extra Storage'),
        ('agents', 'Additional Agents'),  
        ('features', 'Premium Features'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    addon_type = models.CharField(max_length=20, choices=ADDON_TYPES)
    description = models.TextField()
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=20, choices=SubscriptionPlan.BILLING_CYCLES, default='month')
    
    # Features
    extra_minutes = models.IntegerField(default=0)
    extra_storage_gb = models.IntegerField(default=0)
    extra_agents = models.IntegerField(default=0)
    features_included = models.JSONField(default=dict)
    
    # Stripe
    stripe_price_id = models.CharField(max_length=100, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - ${self.price}"


class UserSubscriptionAddon(models.Model):
    """User's active add-ons"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='addons')
    addon = models.ForeignKey(SubscriptionAddon, on_delete=models.CASCADE)
    
    quantity = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"{self.subscription.user.email} - {self.addon.name}"
