import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from restaurants.models import Restaurant


class Command(BaseCommand):
    help = "Seed the database with development restaurants for local search testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="development_restaurants.json",
            help="Fixture filename inside restaurants/fixtures/.",
        )

    def handle(self, *args, **options):
        fixture_path = (
            Path(__file__).resolve().parents[2] / "fixtures" / options["fixture"]
        )

        if not fixture_path.exists():
            raise CommandError(f"Fixture not found: {fixture_path}")

        restaurants = json.loads(fixture_path.read_text())
        created_count = 0
        updated_count = 0

        for restaurant_data in restaurants:
            external_source = restaurant_data.get("external_source")
            external_place_id = restaurant_data.get("external_place_id")

            if not external_source or not external_place_id:
                raise CommandError(
                    "Every seed restaurant needs external_source and external_place_id."
                )

            _, created = Restaurant.objects.update_or_create(
                external_source=external_source,
                external_place_id=external_place_id,
                defaults=restaurant_data,
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(restaurants)} restaurants "
                f"({created_count} created, {updated_count} updated)."
            )
        )
