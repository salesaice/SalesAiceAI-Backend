from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from subscriptions.models import SubscriptionPlan, Subscription, BillingHistory, UsageAlert
from agents.models import Agent, AgentPerformance
from calls.models import CallSession, CallQueue, QuickAction
from dashboard.models import SystemNotification, ActivityLog

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for call center dashboard'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))
        
        # Create subscription plans
        self.create_subscription_plans()
        
        # Create sample users
        self.create_sample_users()
        
        # Create agents
        self.create_agents()
        
        # Create quick actions
        self.create_quick_actions()
        
        # Create notifications
        self.create_notifications()
        
        # Create sample call data
        self.create_sample_calls()
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))

    def create_subscription_plans(self):
        """Create sample subscription plans"""
        plans = [
            {
                'name': 'Basic Plan',
                'plan_type': 'basic',
                'price': Decimal('29.99'),
                'billing_cycle': 'monthly',
                'max_agents': 2,
                'max_minutes': 1000,
                'inbound_calls': True,
                'outbound_calls': True,
                'ai_assistance': False,
                'analytics': False,
            },
            {
                'name': 'Premium Plan',
                'plan_type': 'premium',
                'price': Decimal('79.99'),
                'billing_cycle': 'monthly',
                'max_agents': 10,
                'max_minutes': 5000,
                'inbound_calls': True,
                'outbound_calls': True,
                'ai_assistance': True,
                'analytics': True,
            },
            {
                'name': 'Enterprise Plan',
                'plan_type': 'enterprise',
                'price': Decimal('199.99'),
                'billing_cycle': 'monthly',
                'max_agents': 50,
                'max_minutes': 20000,
                'inbound_calls': True,
                'outbound_calls': True,
                'ai_assistance': True,
                'analytics': True,
            }
        ]
        
        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(f'Created plan: {plan.name}')

    def create_sample_users(self):
        """Create sample users with subscriptions"""
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@callcenter.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'admin',
                'is_active': True,
                'is_verified': True
            }
        )
        if created:
            admin_user.set_password('Admin@123')
            admin_user.save()
            self.stdout.write('Created admin user')
        
        # Create regular users
        users_data = [
            {
                'email': 'john.doe@company.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': 'user',
                'plan': 'Premium Plan'
            },
            {
                'email': 'jane.smith@company.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'role': 'user',
                'plan': 'Basic Plan'
            }
        ]
        
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'role': user_data['role'],
                    'is_active': True,
                    'is_verified': True
                }
            )
            if created:
                user.set_password('User@123')
                user.save()
                
                # Create subscription
                plan = SubscriptionPlan.objects.get(name=user_data['plan'])
                subscription = Subscription.objects.create(
                    user=user,
                    plan=plan,
                    status='active',
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=30),
                    next_billing_date=timezone.now() + timedelta(days=30),
                    minutes_used=500,
                    agents_used=1
                )
                
                # Create billing history
                BillingHistory.objects.create(
                    subscription=subscription,
                    amount=plan.price,
                    status='paid',
                    billing_period_start=timezone.now() - timedelta(days=30),
                    billing_period_end=timezone.now(),
                    paid_at=timezone.now()
                )
                
                self.stdout.write(f'Created user: {user.email}')

    def create_agents(self):
        """Create sample agents"""
        agents_data = [
            {
                'email': 'agent1@callcenter.com',
                'first_name': 'Alice',
                'last_name': 'Johnson',
                'employee_id': 'AGT001',
                'department': 'Sales',
                'status': 'available',
                'skill_level': 'advanced'
            },
            {
                'email': 'agent2@callcenter.com',
                'first_name': 'Bob',
                'last_name': 'Wilson',
                'employee_id': 'AGT002',
                'department': 'Support',
                'status': 'on_call',
                'skill_level': 'intermediate'
            },
            {
                'email': 'agent3@callcenter.com',
                'first_name': 'Carol',
                'last_name': 'Davis',
                'employee_id': 'AGT003',
                'department': 'Sales',
                'status': 'available',
                'skill_level': 'expert'
            }
        ]
        
        for agent_data in agents_data:
            user, created = User.objects.get_or_create(
                email=agent_data['email'],
                defaults={
                    'first_name': agent_data['first_name'],
                    'last_name': agent_data['last_name'],
                    'role': 'agent',
                    'is_active': True,
                    'is_verified': True
                }
            )
            if created:
                user.set_password('Agent@123')
                user.save()
                
                # Create agent profile
                agent = Agent.objects.create(
                    user=user,
                    employee_id=agent_data['employee_id'],
                    department=agent_data['department'],
                    status=agent_data['status'],
                    skill_level=agent_data['skill_level'],
                    total_calls=150,
                    successful_calls=135,
                    average_call_duration=8.5,
                    customer_satisfaction=4.2
                )
                
                # Create performance data
                AgentPerformance.objects.create(
                    agent=agent,
                    date=timezone.now().date(),
                    total_calls=25,
                    answered_calls=23,
                    completed_calls=20,
                    average_talk_time=7.8,
                    customer_satisfaction=4.3,
                    first_call_resolution=18
                )
                
                self.stdout.write(f'Created agent: {user.email}')

    def create_quick_actions(self):
        """Create quick action buttons"""
        actions = [
            {
                'name': 'Inbound Call',
                'action_type': 'call',
                'icon': 'phone-incoming',
                'color': 'success',
                'sort_order': 1
            },
            {
                'name': 'Outbound Call',
                'action_type': 'call',
                'icon': 'phone-outgoing',
                'color': 'primary',
                'sort_order': 2
            },
            {
                'name': 'Send SMS',
                'action_type': 'sms',
                'icon': 'message-circle',
                'color': 'info',
                'sort_order': 3
            },
            {
                'name': 'Schedule Callback',
                'action_type': 'schedule',
                'icon': 'calendar',
                'color': 'warning',
                'sort_order': 4
            }
        ]
        
        for action_data in actions:
            action, created = QuickAction.objects.get_or_create(
                name=action_data['name'],
                defaults=action_data
            )
            if created:
                self.stdout.write(f'Created quick action: {action.name}')

    def create_notifications(self):
        """Create sample notifications"""
        notifications = [
            {
                'title': 'System Maintenance',
                'message': 'Scheduled maintenance will occur tonight from 2:00 AM to 4:00 AM EST.',
                'notification_type': 'maintenance',
                'priority': 'medium',
                'target_roles': ['admin', 'agent']
            },
            {
                'title': 'New Feature Available',
                'message': 'HomeAI integration is now available for Premium and Enterprise plans.',
                'notification_type': 'info',
                'priority': 'low',
                'target_roles': ['user', 'admin']
            }
        ]
        
        admin_user = User.objects.filter(role='admin').first()
        for notif_data in notifications:
            notification = SystemNotification.objects.create(
                title=notif_data['title'],
                message=notif_data['message'],
                notification_type=notif_data['notification_type'],
                priority=notif_data['priority'],
                target_roles=notif_data['target_roles'],
                created_by=admin_user
            )
            self.stdout.write(f'Created notification: {notification.title}')

    def create_sample_calls(self):
        """Create sample call sessions"""
        agents = Agent.objects.all()
        if not agents.exists():
            return
        
        for i in range(10):
            agent = agents[i % len(agents)]
            call = CallSession.objects.create(
                user=agent.user,
                agent=agent,
                call_type='inbound' if i % 2 == 0 else 'outbound',
                status='completed',
                caller_number=f'+1555000{100 + i}',
                callee_number='+15551234567',
                caller_name=f'Customer {i + 1}',
                started_at=timezone.now() - timedelta(hours=i),
                answered_at=timezone.now() - timedelta(hours=i) + timedelta(seconds=30),
                ended_at=timezone.now() - timedelta(hours=i) + timedelta(minutes=5),
                duration=300 + (i * 30),  # 5-10 minutes
                notes=f'Call completed successfully. Customer inquiry resolved.'
            )
            
            # Create activity logs
            ActivityLog.objects.create(
                user=agent.user,
                action='call_start',
                description=f'Started {call.call_type} call with {call.caller_number}',
                metadata={'call_id': str(call.id)}
            )
        
        self.stdout.write(f'Created {CallSession.objects.count()} sample calls')
