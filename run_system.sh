#!/bin/bash

echo "Creating virtual environment..."
python -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt

echo "Importing teams..."
python import_teams.py

echo "Generating QR codes..."
python manage.py generate-qrs --base-url http://127.0.0.1:5000

echo "Starting the server..."
python app.py
