import csv
from django.core.management.base import BaseCommand
from customers.models import Customer, CountryCodes
from users.models import CustomUser
from django.utils.dateparse import parse_datetime
from django.core.files.images import ImageFile
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Import customers from CSV (preserving IDs)'

    def handle(self, *args, **kwargs):
        with open('exported_customers.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    created_by = CustomUser.objects.get(id=row['created_by_id']) if row['created_by_id'] else None
                except CustomUser.DoesNotExist:
                    created_by = None
                    self.stdout.write(f"⚠️ Missing user ID {row['created_by_id']}")

                try:
                    country_code = CountryCodes.objects.get(id=row['country_code_id']) if row['country_code_id'] else None
                except CountryCodes.DoesNotExist:
                    country_code = None
                    self.stdout.write(f"⚠️ Missing country code ID {row['country_code_id']}")

                customer, created = Customer.objects.update_or_create(
                    customer_id=row['customer_id'],
                    defaults={
                        'account_number': row['account_number'],
                        'customer_name': row['customer_name'],
                        'company': row['company'],
                        'country_code': country_code,
                        'customer_phone': row['customer_phone'],
                        'customer_address': row['customer_address'],
                        'email': row['email'],
                        'website': row['website'],
                        'creation_date': parse_datetime(row['creation_date']),
                        'modified_date': parse_datetime(row['modified_date']),
                        'tax_number': row['tax_number'],
                        'created_by': created_by,
                        'notes': row['notes'],
                        'image': row['image'] if row['image'] else 'customers/avatar.png',
                    }
                )

                status = "🆕 Created" if created else "🔁 Updated"
                self.stdout.write(f"{status} customer: {customer.customer_name} (ID {customer.customer_id})")

        self.stdout.write(self.style.SUCCESS("✅ All customers imported successfully!"))
