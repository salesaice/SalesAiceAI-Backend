from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create admin user'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Admin email')
        parser.add_argument('--password', type=str, help='Admin password')
        parser.add_argument('--name', type=str, help='Admin name')

    def handle(self, *args, **options):
        email = options.get('email') or input('Enter admin email: ')
        password = options.get('password') or input('Enter admin password: ')
        name = options.get('name') or input('Enter admin name: ')
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'User with email {email} already exists!')
            )
            return
        
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=name,
            role='admin',
            is_staff=True,
            is_superuser=True,
            is_verified=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Admin user {email} created successfully!')
        )
