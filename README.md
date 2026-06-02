# MINDS

MINDS (Memorandum Information Notification Distribution System) is an office memorandum distribution system built with Django.

## Setup

```bash
# Clone this repository locally
git clone https://github.com/TheoDrHashiriya/MINDS.git

# Navigate to the local repo
cd MINDS

# Rename the `.env.sample` to `.env` and fill in each field as needed
mv .env.sample .env
nano .env

# Create a virtual environment
python -m venv .venv

# Load initial data into the database
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

## Usage

```bash
# Activate its virtual environment
source .venv/bin/activate

# Run a local server
python manage.py runserver
```
