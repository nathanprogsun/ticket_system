import uuid
from django.core.management.base import BaseCommand
from order.models import Order
from ticket.models import Ticket
from faker import Faker


class Command(BaseCommand):
    help = "Seed ticket data"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=1000000)
        parser.add_argument("--batch-size", type=int, default=1000)

    def handle(self, *args, **options):
        count = options["count"]
        batch_size = options["batch_size"]
        fake = Faker()

        # Use iterator instead of list to reduce memory usage
        order_ids = Order.objects.values_list("id", flat=True).iterator()
        order_ids = list(order_ids)  # Convert to list for reuse

        if not order_ids:
            self.stdout.write("No orders found. Please run seed_orders first")
            return

        self.stdout.write(f"Creating {count} tickets...")

        # Process in batches of 1000 records
        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            tickets = [
                Ticket(
                    order_id=fake.random_element(order_ids),
                    name=fake.name(),
                    token=uuid.uuid4().hex,
                )
                for _ in range(batch_count)
            ]
            Ticket.objects.bulk_create(tickets)
            self.stdout.write(f"Progress: {i + batch_count}/{count} tickets created")

        self.stdout.write(self.style.SUCCESS(f"Successfully created {count} tickets"))
