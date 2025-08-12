import csv
from django.core.management.base import BaseCommand
from users.models import CustomUser, Profile
from django.contrib.auth.models import Group
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Import users with IDs from CSV file'

    def handle(self, *args, **kwargs):
        group_map = {
            'Graphics': Group.objects.get_or_create(name='Graphics')[0],
            'Sales': Group.objects.get_or_create(name='Sales')[0],
            'IT Department': Group.objects.get_or_create(name='IT')[0],
            'Accounting': Group.objects.get_or_create(name='Accounting')[0],
            'Managers': Group.objects.get_or_create(name='Managers')[0],
            'Developer': Group.objects.get_or_create(name='Developer')[0],
            'Cashier': Group.objects.get_or_create(name='Cashier')[0],
        }

        with open('exported_users.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                user, created = CustomUser.objects.update_or_create(
                    id=row['id'],
                    defaults={
                        'username': row['username'],
                        'email': row['email'],
                        'first_name': row['first_name'],
                        'last_name': row['last_name'],
                        'is_active': row['is_active'] == 'True',
                        'is_staff': row['is_staff'] == 'True',
                        'is_superuser': row['is_superuser'] == 'True',
                        'last_login': parse_datetime(row['last_login']) if row['last_login'] else None,
                        'date_joined': parse_datetime(row['date_joined']) if row['date_joined'] else None,
                        'password': row['password'],  # hashed password
                    }
                )

                # Profile creation
                Profile.objects.update_or_create(
                    user=user,
                    defaults={
                        'mobile': row['mobile'],
                        'address': row['address'],
                        'bio': row['bio'],
                        'total_jobs': row['total_jobs'],
                        'finished_jobs': row['finished_jobs'],
                        'unfinished_jobs': row['unfinished_jobs'],
                    }
                )

                # Assign group
                department = row['department']
                user.groups.clear()
                if department in group_map:
                    user.groups.add(group_map[department])

                self.stdout.write(f"✅ Imported user {user.username} with ID {user.id}")
