import itertools
import random
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

        order_count = Order.objects.count()
        if not order_count:
            self.stdout.write("No orders found. Please run seed_orders first")
            return

        # Use iterator instead of list to reduce memory usage
        order_ids_iterator = Order.objects.values_list("id", flat=True).iterator()

        self.stdout.write(f"Creating {count} tickets...")

        # Process in batches of 1000 records
        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            slice_order_ids = list(
                itertools.islice(order_ids_iterator, min(batch_count, order_count))
            )  # Get a slice of order IDs as a list
            tickets = [
                Ticket(
                    order_id=random.choice(
                        slice_order_ids
                    ),  # Randomly select an order ID from the list
                    name=fake.name(),
                    token=uuid.uuid4().hex,
                )
                for _ in range(batch_count)
            ]
            Ticket.objects.bulk_create(tickets)
            self.stdout.write(f"Progress: {i + batch_count}/{count} tickets created")

        self.stdout.write(self.style.SUCCESS(f"Successfully created {count} tickets"))
