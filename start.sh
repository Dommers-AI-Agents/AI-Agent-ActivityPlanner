#!/bin/bash
# Script to start the AI Activity Planner application

echo "Starting AI Activity Planner..."

# Run docker-compose up in detached mode
docker-compose up -d

# Start main.py in the background
echo "Starting main.py in background mode..."
nohup python main.py > app.log 2>&1 &

echo "Application started successfully."
echo "- Web server is running with Docker"
echo "- main.py is running in the background (logs in app.log)"