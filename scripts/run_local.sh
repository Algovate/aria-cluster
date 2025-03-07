#!/bin/bash
# Script to run the aria2c cluster locally

# Check dependencies
echo "Checking dependencies..."
python scripts/check_dependencies.py
if [ $? -ne 0 ]; then
    echo "Error: Failed to check or install dependencies."
    exit 1
fi

# Create necessary directories
echo "Setting up directories..."
python scripts/setup.py

# Start the dispatcher in the background
echo "Starting dispatcher..."
python scripts/run_dispatcher.py &
DISPATCHER_PID=$!

# Wait for the dispatcher to start
echo "Waiting for dispatcher to start..."
sleep 5

# Start the first worker in the background
echo "Starting worker 1..."
CONFIG_PATH=config/worker.json python scripts/run_worker.py &
WORKER1_PID=$!

# Start the second worker in the background
echo "Starting worker 2..."
CONFIG_PATH=config/worker2.json python scripts/run_worker.py &
WORKER2_PID=$!

echo "Aria2c cluster is running!"
echo "Dispatcher PID: $DISPATCHER_PID"
echo "Worker 1 PID: $WORKER1_PID"
echo "Worker 2 PID: $WORKER2_PID"
echo ""
echo "Press Ctrl+C to stop all processes"

# Wait for Ctrl+C
trap "echo 'Stopping all processes...'; kill $DISPATCHER_PID $WORKER1_PID $WORKER2_PID; exit 0" INT
wait 