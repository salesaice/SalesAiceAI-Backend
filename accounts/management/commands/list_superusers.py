from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'List all superusers'

    def handle(self, *args, **options):
        superusers = User.objects.filter(is_superuser=True)
        
        self.stdout.write(
            self.style.SUCCESS('=' * 50)
        )
        self.stdout.write(
            self.style.SUCCESS('SUPERUSERS LIST')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 50)
        )
        
        if superusers.exists():
            for user in superusers:
                self.stdout.write(
                    f"📧 Email: {user.email}"
                )
                self.stdout.write(
                    f"👤 Name: {user.first_name} {user.last_name}"
                )
                self.stdout.write(
                    f"🎭 Role: {user.role}"
                )
                self.stdout.write(
                    f"🏢 Staff: {'Yes' if user.is_staff else 'No'}"
                )
                self.stdout.write(
                    f"✅ Active: {'Yes' if user.is_active else 'No'}"
                )
                self.stdout.write(
                    f"📅 Date Joined: {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                self.stdout.write("-" * 30)
            
            self.stdout.write(
                self.style.SUCCESS(f"\nTotal Superusers: {superusers.count()}")
            )
        else:
            self.stdout.write(
                self.style.WARNING("No superusers found!")
            )
