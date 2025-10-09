from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Create subscription packages according to dashboard image'

    def handle(self, *args, **options):
        self.stdout.write('Creating subscription packages based on dashboard image...')
        
        # Clear existing plans
        SubscriptionPlan.objects.all().delete()
        
        # Create Starter Package
        starter = SubscriptionPlan.objects.create(
            name='Starter',
            plan_type='starter',
            price=29.00,
            call_minutes_limit=1000,  # 1000 minutes monthly
            minutes_inbound_limit=500,  # 500 inbound minutes
            minutes_outbound_limit=500,  # 500 outbound minutes
            agents_allowed=1,
            analytics_access=False,
            advanced_analytics=False,
            stripe_price_id='',  # Will be added later
            stripe_product_id='',
            is_active=True
        )
        
        # Create Pro Package (Most Popular)
        pro = SubscriptionPlan.objects.create(
            name='Pro',
            plan_type='pro', 
            price=99.00,
            call_minutes_limit=3000,  # 3000 minutes monthly
            minutes_inbound_limit=1500,  # 1500 inbound minutes
            minutes_outbound_limit=1500,  # 1500 outbound minutes
            agents_allowed=5,
            analytics_access=True,
            advanced_analytics=False,
            stripe_price_id='',  # Will be added later
            stripe_product_id='',
            is_active=True
        )
        
        # Create Enterprise Package
        enterprise = SubscriptionPlan.objects.create(
            name='Enterprise',
            plan_type='enterprise',
            price=299.00,
            call_minutes_limit=10000,  # 10000 minutes monthly
            minutes_inbound_limit=5000,  # 5000 inbound minutes
            minutes_outbound_limit=5000,  # 5000 outbound minutes
            agents_allowed=25,
            analytics_access=True,
            advanced_analytics=True,  # API access included
            stripe_price_id='',  # Will be added later
            stripe_product_id='',
            is_active=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {SubscriptionPlan.objects.count()} subscription packages:'
            )
        )
        
        self.stdout.write('📦 STARTER PACKAGE:')
        self.stdout.write(f'   💰 ${starter.price}/month')
        self.stdout.write(f'   📞 {starter.call_minutes_limit} call minutes')
        self.stdout.write(f'   🤖 {starter.agents_allowed} agent allowed')
        self.stdout.write(f'   📊 Analytics: {"✅" if starter.analytics_access else "❌"}')
        
        self.stdout.write('\n🚀 PRO PACKAGE (RECOMMENDED):')
        self.stdout.write(f'   💰 ${pro.price}/month')
        self.stdout.write(f'   📞 {pro.call_minutes_limit} call minutes')
        self.stdout.write(f'   🤖 {pro.agents_allowed} agents allowed')
        self.stdout.write(f'   📊 Analytics: {"✅" if pro.analytics_access else "❌"}')
        
        self.stdout.write('\n🏢 ENTERPRISE PACKAGE:')
        self.stdout.write(f'   💰 ${enterprise.price}/month')
        self.stdout.write(f'   📞 {enterprise.call_minutes_limit} call minutes')
        self.stdout.write(f'   🤖 {enterprise.agents_allowed} agents allowed')
        self.stdout.write(f'   📊 Analytics: {"✅" if enterprise.analytics_access else "❌"}')
        self.stdout.write(f'   🔧 API Access: {"✅" if enterprise.advanced_analytics else "❌"}')
        
        self.stdout.write('\n✅ Packages setup complete!')
        self.stdout.write('🔑 Add your Stripe keys in settings.py to enable payments')
        self.stdout.write('🎯 Users will see package selection on first login')
