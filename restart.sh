#!/bin/bash
# Script to restart the AI Activity Planner application

echo "Restarting AI Activity Planner..."

# Find and kill the running main.py process
echo "Stopping main.py process..."
pkill -f "python main.py" || echo "No main.py process found running"

# Stop and restart Docker containers
echo "Restarting Docker containers..."
docker-compose down
docker-compose up -d

# Start main.py in the background again
echo "Starting main.py in background mode..."
nohup python main.py > app.log 2>&1 &

echo "Application restarted successfully."
echo "- Web server is running with Docker"
echo "- main.py is running in the background (logs in app.log)"