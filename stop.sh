#!/bin/bash
# Script to stop the AI Activity Planner application

echo "Stopping AI Activity Planner..."

# Find and kill the running main.py process
echo "Stopping main.py process..."
pkill -f "python main.py" || echo "No main.py process found running"

# Stop Docker containers
echo "Stopping Docker containers..."
docker-compose down

echo "Application stopped successfully."