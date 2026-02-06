#!/bin/bash
# Wrapper script to run SolarVille simulation

# Check if venv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH=$(pwd)

# Default to prosumer (pi1) if no device specified
DEVICE=${1:-pi1}

echo "=== Starting SolarVille Simulation ==="
echo "Device: $DEVICE"
echo "Press Ctrl+C to stop"
echo "=================================="
echo ""

# Run the simulation with unbuffered output
venv/bin/python3 -u core/main.py --mock --device "$DEVICE" 2>&1
