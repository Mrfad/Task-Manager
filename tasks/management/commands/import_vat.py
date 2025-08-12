import csv
from django.core.management.base import BaseCommand
from tasks.models import Vat

class Command(BaseCommand):
    help = 'Import VAT data from CSV'

    def handle(self, *args, **kwargs):
        with open('exported_vat.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                Vat.objects.update_or_create(
                    id=row['id'],
                    defaults={
                        'name': row['name'],
                        'value': row['value'],
                    }
                )
        self.stdout.write(self.style.SUCCESS("✅ VAT imported"))
