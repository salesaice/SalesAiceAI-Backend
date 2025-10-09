from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class DashboardWidget(models.Model):
    """Dashboard widgets for different user roles"""
    WIDGET_TYPES = [
        ('stats', 'Statistics'),
        ('chart', 'Chart'),
        ('list', 'List'),
        ('quick_action', 'Quick Action'),
        ('notifications', 'Notifications'),
        ('calendar', 'Calendar'),
    ]
    
    USER_ROLES = [
        ('admin', 'Admin'),
        ('user', 'User'),
        ('agent', 'Agent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    role = models.CharField(max_length=20, choices=USER_ROLES)
    
    # Widget configuration
    config = models.JSONField(default=dict, blank=True)
    
    # Layout
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=4)
    height = models.IntegerField(default=3)
    
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['role', 'sort_order']
    
    def __str__(self):
        return f"{self.name} ({self.role})"


class UserDashboardPreference(models.Model):
    """User-specific dashboard preferences"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard_preferences')
    
    # Layout preferences
    theme = models.CharField(max_length=20, default='light')
    sidebar_collapsed = models.BooleanField(default=False)
    
    # Widget preferences
    widgets_config = models.JSONField(default=dict, blank=True)
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Dashboard Preferences - {self.user.email}"


class SystemNotification(models.Model):
    """System-wide notifications"""
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
        ('maintenance', 'Maintenance'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    
    # Target audience
    target_roles = models.JSONField(default=list, blank=True)  # ['admin', 'user', 'agent']
    target_users = models.ManyToManyField(User, blank=True)
    
    # Scheduling
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.notification_type})"


class ActivityLog(models.Model):
    """System activity logs"""
    ACTION_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('call_start', 'Call Started'),
        ('call_end', 'Call Ended'),
        ('subscription_change', 'Subscription Change'),
        ('payment', 'Payment'),
        ('user_create', 'User Created'),
        ('user_update', 'User Updated'),
        ('agent_status', 'Agent Status Change'),
        ('system_config', 'System Configuration'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.created_at}"
