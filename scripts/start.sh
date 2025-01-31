#!/bin/bash
# Exit on errors and show commands
set -eo pipefail

# Create fresh venv if doesn't exist
if [ ! -d "env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv env
    source env/bin/activate
    echo "Upgrading pip and installing dependencies..."
    pip install --upgrade pip
    pip install -e .[dev]
else
    echo "Activating existing virtual environment..."
    source env/bin/activate
fi

# Check for installed packages
echo "Checking installed packages:"
pip list | grep -E 'mysql-connector-python|discord|openai'

# Run the bot with explicit path
echo "Starting bot..."
python -m linkbot