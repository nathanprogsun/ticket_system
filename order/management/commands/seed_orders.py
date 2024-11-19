from django.core.management.base import BaseCommand
from user.models import User
from order.models import Order
from faker import Faker


class Command(BaseCommand):
    help = "Seed order data"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=10000)
        parser.add_argument("--batch-size", type=int, default=1000)

    def handle(self, *args, **options):
        count = options["count"]
        batch_size = options["batch_size"]
        fake = Faker()

        # Get all user IDs or exit if no users exist
        user_ids = list(User.objects.values_list("id", flat=True))
        if not user_ids:
            self.stdout.write(
                self.style.ERROR("No users found. Please run seed_users first")
            )
            return

        self.stdout.write(f"Creating {count} orders...")

        # Process in batches to handle large datasets
        total_created = 0
        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            orders = [
                Order(
                    user_id=fake.random_element(user_ids),
                    name=fake.name(),
                )
                for _ in range(batch_count)
            ]

            # Bulk create current batch
            Order.objects.bulk_create(orders)
            total_created += batch_count

            # Show progress
            progress = (total_created / count) * 100
            self.stdout.write(
                f"Progress: {total_created}/{count} orders created ({progress:.1f}%)"
            )

        self.stdout.write(self.style.SUCCESS(f"Successfully created {count} orders"))
