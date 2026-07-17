from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Safely reset and reseed the standalone demo database."

    def handle(self, *args, **options):
        call_command("seed_demo_data", "--yes")
