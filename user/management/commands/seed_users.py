import random
from django.core.management.base import BaseCommand
from user.models import User
from faker import Faker


class Command(BaseCommand):
    help = "Seed user data"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=1000)

    def handle(self, *args, **options):
        count = options["count"]
        self.stdout.write(f"Creating {count} users...")

        # Define allowed email domains
        domains = ["gmail.com", "example.com", "outlook.com"]
        fake = Faker()

        # Prepare list of user objects for bulk creation
        users = [
            User(
                email=fake.email(domain=random.choice(domains)),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                password=fake.password(),
            )
            for _ in range(count)
        ]

        # Bulk create all users in a single query
        created_users = User.objects.bulk_create(users)

        # Log created users
        for user in created_users:
            self.stdout.write(f"Created user: {user.email}")
