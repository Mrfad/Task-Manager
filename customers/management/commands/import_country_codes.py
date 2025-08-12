from django.core.management.base import BaseCommand
from customers.models import CountryCodes
import csv

class Command(BaseCommand):  # <- ✅ MUST be named exactly "Command"
    help = 'Import CountryCodes from CSV (preserving IDs)'

    def handle(self, *args, **kwargs):
        with open('exported_country_codes.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                code, created = CountryCodes.objects.update_or_create(
                    id=row['id'],
                    defaults={
                        'country_name': row['country_name'],
                        'country_code': row['country_code'],
                        'country_phone_code': row['country_phone_code'],
                    }
                )

                status = "🆕 Created" if created else "🔁 Updated"
                self.stdout.write(f"{status} country code: {code.country_name} (ID {code.id})")

        self.stdout.write(self.style.SUCCESS("✅ All CountryCodes imported successfully!"))
