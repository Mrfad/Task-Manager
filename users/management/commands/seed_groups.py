# users/management/commands/seed_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

DEPARTMENTS = [
    'IT',
    'Sales',
    'Accounting',
    'Graphics',
    'Managers',
    'ManagerAssistant',
    'FrontDesk',
    'Developer',
    'Cashier',
]

class Command(BaseCommand):
    help = 'Seed initial user groups based on department names and assign users based on role'

    def handle(self, *args, **kwargs):
        # ✅ Step 1: Ensure all groups exist
        for name in DEPARTMENTS:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✔️ Group created: {name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Already exists: {name}'))

        developer_group = Group.objects.get(name="Developer")
        graphics_group = Group.objects.get(name="Graphics")

        # ✅ Step 2: Assign users to appropriate groups
        users = User.objects.all()
        for user in users:
            if user.groups.exists():
                self.stdout.write(self.style.NOTICE(f'Skipped (already in group): {user.username}'))
                continue

            if user.is_staff or user.is_superuser:
                user.groups.add(developer_group)
                self.stdout.write(self.style.SUCCESS(f'Added to Developer: {user.username}'))
            else:
                user.groups.add(graphics_group)
                self.stdout.write(self.style.SUCCESS(f'Added to Graphics: {user.username}'))
