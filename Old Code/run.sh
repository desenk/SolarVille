# Branch: ProsumerJack
# File: run.sh

#!/bin/bash

# Default values
DATA_FILE="/home/pi/block_0.csv"
START_DATE="2012-10-24"
TIMESCALE="d"
PROSUMER_HOUSEHOLD="MAC000246"  # Default prosumer household ID
PORT=5000  # Default port

# Function to show usage
show_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --file <path>      : Path to data file (default: $DATA_FILE)"
    echo "  --date <YYYY-MM-DD>: Start date (default: $START_DATE)"
    echo "  --scale <d|w|m|y>  : Timescale (default: $TIMESCALE)"
    echo "  --household <id>   : Household ID (default: $PROSUMER_HOUSEHOLD)"
    echo "Example:"
    echo "  $0 --file /home/pi/block_0.csv --date 2012-10-24 --scale d --household MAC000246"
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill any existing Flask process on port 5000
cleanup_existing() {
    echo "Checking for existing Flask server..."
    local pid=$(lsof -ti:$PORT)
    if [ ! -z "$pid" ]; then
        echo "Found existing server on port $PORT (PID: $pid)"
        echo "Stopping existing server..."
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

# Function to cleanup our processes on script exit
cleanup() {
    echo "Cleaning up..."
    if [ -f "server.pid" ]; then
        SERVER_PID=$(cat server.pid)
        kill -9 $SERVER_PID 2>/dev/null
        rm server.pid
    fi
}

# Register cleanup function to run on script exit
trap cleanup EXIT

# Parse optional arguments
while [ $# -gt 0 ]; do
    case $1 in
        --file)
            DATA_FILE="$2"
            shift 2
            ;;
        --date)
            START_DATE="$2"
            shift 2
            ;;
        --scale)
            TIMESCALE="$2"
            shift 2
            ;;
        --household)
            PROSUMER_HOUSEHOLD="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Clean up any existing Flask server
cleanup_existing

echo "Starting server..."
# Start the server in the background and save its PID
FLASK_PORT=$PORT python server.py &
SERVER_PID=$!
echo $SERVER_PID > server.pid

# Wait for server to start and verify it's running
max_attempts=10
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:$PORT/health >/dev/null; then
        echo "Server started successfully (PID: $SERVER_PID)"
        break
    fi
    
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "Server failed to start"
        exit 1
    fi
    
    echo "Waiting for server to start (attempt $attempt/$max_attempts)..."
    sleep 1
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "Server failed to start after $max_attempts attempts"
    exit 1
fi

echo "Starting Prosumer simulation..."
echo "File path: $DATA_FILE"
echo "Household ID: $PROSUMER_HOUSEHOLD"
echo "Start date: $START_DATE"
echo "Timescale: $TIMESCALE"

# Run the simulation
python run.py \
    --file_path "$DATA_FILE" \
    --household "$PROSUMER_HOUSEHOLD" \
    --start_date "$START_DATE" \
    --timescale "$TIMESCALE"