#!/bin/bash
# start.sh

# Start FastAPI in the background
uvicorn backend.main:app --reload --port 8000 --log-level debug &
FASTAPI_PID=$!

# Wait a moment for FastAPI to start
sleep 5

# Start Streamlit in the background
streamlit run frontend/app.py
STREAMLIT_PID=$!

# Function to handle termination
cleanup() {
    echo "Shutting down services..."
    kill $FASTAPI_PID
    kill $STREAMLIT_PID
    exit 0
}

# Set up trap for clean termination
trap cleanup SIGINT SIGTERM

# Keep script running
echo "Services started. Press Ctrl+C to stop."
wait
