from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.reference.seed import seed_reference_data


class Command(BaseCommand):
    help = "Idempotently seed sectors, EU-27 countries, Uzbekistan regions/districts, organizations and task template."

    def handle(self, *args, **options):
        with transaction.atomic():
            created = seed_reference_data(apps)
        summary = ", ".join(f"{key}: {value}" for key, value in created.items())
        self.stdout.write(self.style.SUCCESS(f"Reference data seeded (new rows) -> {summary}"))
