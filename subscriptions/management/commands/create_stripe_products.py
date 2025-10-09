from django.core.management.base import BaseCommand
from django.conf import settings
import stripe
from subscriptions.models import SubscriptionPlan

stripe.api_key = settings.STRIPE_SECRET_KEY


class Command(BaseCommand):
    help = 'Create and sync Stripe products and prices for subscription plans'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update existing Stripe products and prices',
        )
        parser.add_argument(
            '--plan-id',
            type=str,
            help='Update specific plan by ID',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating/updating Stripe products and prices...'))
        
        # Filter plans
        if options['plan_id']:
            try:
                plans = [SubscriptionPlan.objects.get(id=options['plan_id'], is_active=True)]
            except SubscriptionPlan.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Plan with ID {options['plan_id']} not found"))
                return
        else:
            plans = SubscriptionPlan.objects.filter(is_active=True)
        
        for plan in plans:
            self.process_plan(plan, options['force_update'])
        
        self.stdout.write(self.style.SUCCESS('Stripe products and prices sync completed!'))
    
    def process_plan(self, plan, force_update=False):
        """Process a single subscription plan"""
        
        # Create or update product
        if not plan.stripe_product_id or force_update:
            try:
                if plan.stripe_product_id and force_update:
                    # Update existing product
                    product = stripe.Product.modify(
                        plan.stripe_product_id,
                        name=plan.name,
                        description=self._get_plan_description(plan),
                        metadata={
                            'plan_id': str(plan.id),
                            'plan_type': plan.plan_type,
                            'agents_allowed': str(plan.agents_allowed),
                            'call_minutes_limit': str(plan.call_minutes_limit),
                        }
                    )
                    self.stdout.write(f'Updated product: {plan.name} ({product.id})')
                else:
                    # Create new product
                    product = stripe.Product.create(
                        name=plan.name,
                        description=self._get_plan_description(plan),
                        metadata={
                            'plan_id': str(plan.id),
                            'plan_type': plan.plan_type,
                            'agents_allowed': str(plan.agents_allowed),
                            'call_minutes_limit': str(plan.call_minutes_limit),
                        }
                    )
                    self.stdout.write(f'Created product: {plan.name} ({product.id})')
                
                plan.stripe_product_id = product.id
                plan.save()
                    
            except stripe.error.StripeError as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating/updating product for {plan.name}: {str(e)}')
                )
                return
        
        # Create prices for both monthly and yearly cycles
        self.create_or_update_price(plan, 'monthly', force_update)
        self.create_or_update_price(plan, 'yearly', force_update)
    
    def create_or_update_price(self, plan, billing_cycle, force_update=False):
        """Create or update price for a specific billing cycle"""
        
        # Calculate price based on billing cycle
        if billing_cycle == 'yearly':
            # 20% discount for yearly plans
            unit_amount = int(plan.price * 100 * 12 * 0.8)
            interval = 'year'
        else:
            unit_amount = int(plan.price * 100)
            interval = 'month'
        
        # Check if price already exists for this cycle
        price_field = f'stripe_price_id_{billing_cycle}' if billing_cycle == 'yearly' else 'stripe_price_id'
        current_price_id = getattr(plan, price_field, None)
        
        if not current_price_id or force_update:
            try:
                if current_price_id and force_update:
                    # Archive old price and create new one (Stripe doesn't allow price updates)
                    stripe.Price.modify(current_price_id, active=False)
                    self.stdout.write(f'Archived old price: {current_price_id}')
                
                # Create new price
                price = stripe.Price.create(
                    product=plan.stripe_product_id,
                    unit_amount=unit_amount,
                    currency='usd',
                    recurring={
                        'interval': interval,
                        'interval_count': 1,
                    },
                    metadata={
                        'plan_id': str(plan.id),
                        'billing_cycle': billing_cycle,
                        'plan_type': plan.plan_type,
                    }
                )
                
                # Save the price ID
                setattr(plan, price_field, price.id)
                plan.save()
                
                self.stdout.write(f'Created {billing_cycle} price for {plan.name}: ${unit_amount/100} ({price.id})')
                
            except stripe.error.StripeError as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating {billing_cycle} price for {plan.name}: {str(e)}')
                )
    
    def _get_plan_description(self, plan):
        """Generate plan description"""
        features = []
        
        if plan.call_minutes_limit:
            features.append(f"{plan.call_minutes_limit:,} call minutes")
        if plan.agents_allowed:
            features.append(f"{plan.agents_allowed} AI agents")
        if plan.analytics_access:
            features.append("Advanced analytics")
        if plan.api_access:
            features.append("API access") 
        if plan.priority_support:
            features.append("Priority support")
        if plan.white_label:
            features.append("White label")
        
        return f"{plan.name} plan - {', '.join(features)}"
                            'plan_type': plan.plan_type
                        }
                    )
                    
                    plan.stripe_price_id = price.id
                    plan.save()
                    
                    self.stdout.write(f'Created price: {plan.name} (${plan.price}/{plan.billing_cycle}) - {price.id}')
                    
                except stripe.error.StripeError as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error creating price for {plan.name}: {str(e)}')
                    )
                    continue
        
        self.stdout.write(self.style.SUCCESS('Stripe products and prices created successfully!'))
