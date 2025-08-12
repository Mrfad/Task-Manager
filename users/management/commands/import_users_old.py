import csv
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        User = get_user_model()
        filename = 'users.csv'
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['username'] == '':
                    row['username'] = f"user{row['id']}"
                    print(f"Generated default username for user {row['id']}: {row['username']}")
                try:
                    user, created = User.objects.get_or_create(
                        username=row['username'],
                        email=row['email'] or '',
                        first_name=row['first_name'] or '',
                        last_name=row['last_name'] or '',
                        is_active=row['is_active'] == 'True',
                        is_staff=row['is_staff'] == 'True',
                        is_superuser=row['is_superuser'] == 'True'
                    )
                    if created:
                        user.set_password(make_password('password123'))  # set a default password
                        user.save()
                        print(f"User {row['username']} created")
                    else:
                        print(f"User {row['username']} already exists")
                except Exception as e:
                    print(f"Error importing user {row['username']}: {e}")