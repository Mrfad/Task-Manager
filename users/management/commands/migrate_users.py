# appv2/users/management/commands/migrate_users.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from users.models import CustomUser, Profile  # appv2 models

from django.db import connections
from django.contrib.auth.hashers import make_password

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Migrate users from AppV1 to AppV2 with profiles and manual group assignment"

    def handle(self, *args, **kwargs):
        self.stdout.write("🔄 Starting user migration...")

        # Connect to legacy DB (appv1)
        appv1_cursor = connections['appv1'].cursor()

        # Query all users from appv1
        from django.contrib.auth.models import User as LegacyUser
        from appv1.models import Profile as LegacyProfile

        old_users = LegacyUser.objects.using('appv1').all()

        # Preload AppV2 groups
        group_map = {
            'Graphics': Group.objects.get_or_create(name='Graphics')[0],
            'Sales': Group.objects.get_or_create(name='Sales')[0],
            'IT Department': Group.objects.get_or_create(name='IT')[0],
            'Accounting': Group.objects.get_or_create(name='Accounting')[0],
            'Managers': Group.objects.get_or_create(name='Managers')[0],
            'Developer': Group.objects.get_or_create(name='Developer')[0],
            'Cashier': Group.objects.get_or_create(name='Cashier')[0],
        }

        for user in old_users:
            # Create or update CustomUser in appv2
            new_user, created = CustomUser.objects.update_or_create(
                id=user.id,  # Preserve ID
                defaults={
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_active': user.is_active,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'last_login': user.last_login,
                    'date_joined': user.date_joined,
                    'password': user.password,  # Preserve hashed password
                }
            )

            # Migrate profile data
            try:
                old_profile = LegacyProfile.objects.using('appv1').get(user=user)

                profile, _ = Profile.objects.update_or_create(
                    user=new_user,
                    defaults={
                        'mobile': old_profile.mobile,
                        'address': old_profile.address,
                        'bio': old_profile.bio,
                        'total_jobs': old_profile.total_jobs,
                        'finished_jobs': old_profile.finished_jobs,
                        'unfinished_jobs': old_profile.unfinished_jobs,
                        'profile_picture': old_profile.image,
                    }
                )

                # Manual group assignment based on department
                department = old_profile.department
                new_user.groups.clear()
                if department in group_map:
                    new_user.groups.add(group_map[department])

            except LegacyProfile.DoesNotExist:
                logger.warning(f"No profile found for user {user.username}")

            self.stdout.write(f"✅ Migrated {new_user.username} (ID: {new_user.id})")

        self.stdout.write(self.style.SUCCESS("🎉 All users and profiles migrated successfully!"))
