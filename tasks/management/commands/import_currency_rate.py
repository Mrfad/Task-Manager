import csv
from django.core.management.base import BaseCommand
from tasks.models import CurrencyRate
from users.models import CustomUser
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Import CurrencyRate from CSV'

    def handle(self, *args, **kwargs):
        with open('exported_currency_rates.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                CurrencyRate.objects.update_or_create(
                    id=row['id'],
                    defaults={
                        'usd_to_lbp': row['currency_rate'],
                        'updated_at': parse_datetime(row['modified_date']) or None,
                    }
                )

        self.stdout.write(self.style.SUCCESS("✅ Currency rates imported"))
