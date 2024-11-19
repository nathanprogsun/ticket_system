# Ticket System
This project was generated using Django.

[toc]

## How to Set Up
This project uses Python as the main language, Pyenv to manage Python environments, and Poetry to manage dependencies.

### Step 1: Install Pyenv
Pyenv is used to manage multiple Python versions in Unix-like systems for each project or globally. To install:

```shell
# 1. Install Pyenv via Homebrew
brew update
brew install pyenv

# 2.1 For Zsh
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# 2.2 For Bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
echo 'eval "$(pyenv init -)"' >> ~/.bash_profile

# 2.3 Restart the shell
exec "$SHELL"
```
Find the most up-to-date installation guide on the [Pyenv GitHub page](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation).

### Step 2: Install Poetry
Poetry is used to manage project dependencies. To install:
- Follow the Poetry [installation guide](https://python-poetry.org/docs/#installing-with-pipx).

### Step 3: Set Up Python Environment
Poetry and Pyenv are used together to manage project Python dependencies.

```bash
# Install Python 3.12
pyenv install 3.12

# Set the default Python version for the project locally
# In the project root
pyenv local 3.12

# Verify the current Python version is set correctly
python --version

# Configure Poetry virtual environment to be located within the project (easier to find for IDE and yourself)
poetry config virtualenvs.in-project true

# Remove any pre-existing Poetry environments, in case of migrating from a legacy setup guide
poetry env remove --all

# Explicitly tell Poetry to use Python 3.12
poetry env use 3.12

# Validate the correct Python version is set up with the following command
poetry env info

# Install both production and development dependencies
poetry install --with dev --sync

# To run the project locally through the shell
poetry run python manage.py runserver
```

### Step 4: Set Up Database
MySQL and Redis are used for database management.

```shell
# Start only the necessary dependency containers, allowing the app to run or perform testing on the host
make docker-start
```

## Local Run and Debugging
### Run the Commands to Generate Tokens for Tickets
1. Migrate the database for an empty database:
   ```bash
   poetry run python manage.py migrate
   ```

2. Seed the objects (user/order/tickets):
   ```bash
   poetry run python manage.py seed_users --count=1000
   poetry run python manage.py seed_orders --count=10000
   poetry run python manage.py seed_tickets --count=1000000
   ```

3. Generate tokens for tickets:
   ```bash
   poetry run python manage.py regenerate_tokens
   poetry run python manage.py regenerate_tokens --help # Show this help message
   poetry run python manage.py regenerate_tokens --resume # Resume from the last saved position
   ```

Results:
![Generate Tokens](/generate_tokens.png)
![Resume Generating Tokens](/resume_generating_tokens.png)

## Project Structure
```bash -I '__pycache__'
$ tree .
├── Makefile
├── README
├── core
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py # Main configuration settings for the project
│   ├── urls.py
│   └── wsgi.py
├── docker-compose.yml
├── manage.py
├── order
│   └── views.py
├── poetry.lock
├── pyproject.toml
├── ticket
│   ├── management
│   │   ├── __init__.py
│   │   └── commands
│   │       ├── __init__.py
│   │       ├── data
│   │       ├── regenerate_tokens.py
│   │       └── seed_tickets.py
│   └── views.py
├── user
└── utils
    └── basemodel.py
```


## Token Regeneration Solution Summary

Solution for batch token regeneration of million-level tickets:

### Implementation Approach
- Batch processing strategy with 1000 records per batch(batch-size can be changed)
- Asynchronous concurrent processing for improved efficiency
- Checkpoint mechanism for progress tracking and recovery
- Task queue implementation for concurrency control

### Key Considerations
- Database Performance: Batch updates to reduce database load
- Memory Management: Chunked loading to prevent memory overflow
- Processing Efficiency: Async operations for enhanced throughput
- Reliability: Checkpoint system ensures task recoverability
- Monitoring: Real-time logging of processing progress
