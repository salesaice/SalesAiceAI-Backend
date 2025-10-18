from django.apps import AppConfig


class HumeaitwilioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'HumeAiTwilio'
    verbose_name = 'HumeAI Twilio Integration'

    def ready(self):
        """
        Import signals when the app is ready
        """
        try:
            import HumeAiTwilio.signals
        except ImportError:
            pass
