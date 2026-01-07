from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Set admin password to admin123'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        try:
            admin = User.objects.get(username='admin')
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Password set successfully for admin user'))
            self.stdout.write('Username: admin')
            self.stdout.write('Password: admin123')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Admin user not found'))
