# Makefile

# Define the Docker Compose file
COMPOSE_FILE=docker-compose.yml

# Start Docker Compose containers
docker-start:
	docker-compose -f $(COMPOSE_FILE) up -d  # Start containers in detached mode

# Migrate the database
migrate:
	poetry run python manage.py migrate && echo "Database migration completed."  # Run migrations with log output

# Seed users
seed_users:
	poetry run python manage.py seed_users --count=1000 && echo "Seeded 1000 users."  # Seed users with log output

# Seed orders
seed_orders:
	poetry run python manage.py seed_orders --count=10000 && echo "Seeded 10000 orders."  # Seed orders with log output

# Seed tickets
seed_tickets:
	poetry run python manage.py seed_tickets --count=1000000 && echo "Seeded 1000000 tickets."  # Seed tickets with log output

# Seed all data
seed: seed_users seed_orders seed_tickets  # Run all seeding commands
