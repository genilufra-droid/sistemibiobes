import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or reset the Django admin user from environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_ADMIN_USERNAME", "admin").strip()
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "")

        if not password:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_ADMIN_PASSWORD is not set; admin reset skipped."
                )
            )
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True

        if hasattr(user, "active"):
            user.active = True
        if hasattr(user, "role"):
            user.role = "SUPER_ADMIN"

        user.set_password(password)
        user.save()

        action = "created" if created else "reset"
        self.stdout.write(self.style.SUCCESS(f"Admin user '{username}' {action} successfully."))
