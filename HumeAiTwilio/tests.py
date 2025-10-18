from django.test import TestCase
from django.contrib.auth.models import User
from .models import HumeAgent, TwilioCall, ConversationLog, CallAnalytics
import uuid


class HumeAgentTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.agent = HumeAgent.objects.create(
            name='Test Agent',
            hume_config_id='test-config-id',
            status='active',
            created_by=self.user
        )
    
    def test_agent_creation(self):
        """Test that agent is created successfully"""
        self.assertEqual(self.agent.name, 'Test Agent')
        self.assertEqual(self.agent.status, 'active')
        self.assertIsInstance(self.agent.id, uuid.UUID)
    
    def test_agent_str(self):
        """Test string representation"""
        expected = f"{self.agent.name} ({self.agent.status})"
        self.assertEqual(str(self.agent), expected)


class TwilioCallTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.agent = HumeAgent.objects.create(
            name='Test Agent',
            hume_config_id='test-config-id',
            created_by=self.user
        )
        self.call = TwilioCall.objects.create(
            call_sid='CA1234567890',
            from_number='+1234567890',
            to_number='+0987654321',
            direction='outbound',
            status='initiated',
            agent=self.agent
        )
    
    def test_call_creation(self):
        """Test that call is created successfully"""
        self.assertEqual(self.call.call_sid, 'CA1234567890')
        self.assertEqual(self.call.status, 'initiated')
        self.assertEqual(self.call.agent, self.agent)
    
    def test_call_str(self):
        """Test string representation"""
        expected = f"{self.call.from_number} → {self.call.to_number} ({self.call.status})"
        self.assertEqual(str(self.call), expected)


class ConversationLogTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.agent = HumeAgent.objects.create(
            name='Test Agent',
            hume_config_id='test-config-id',
            created_by=self.user
        )
        self.call = TwilioCall.objects.create(
            call_sid='CA1234567890',
            from_number='+1234567890',
            to_number='+0987654321',
            agent=self.agent
        )
        self.log = ConversationLog.objects.create(
            call=self.call,
            role='user',
            message='Hello, I need help',
            sentiment='neutral',
            confidence=0.85
        )
    
    def test_log_creation(self):
        """Test that conversation log is created successfully"""
        self.assertEqual(self.log.role, 'user')
        self.assertEqual(self.log.message, 'Hello, I need help')
        self.assertEqual(self.log.sentiment, 'neutral')
