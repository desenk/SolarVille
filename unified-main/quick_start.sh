#!/bin/bash
# Quick start script for SolarVille Phase 1

set -e

echo "=== SolarVille Phase 1 Setup ==="

# Check if we're in unified-main directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Run this script from unified-main directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Run the Phase 1 test:"
echo "  source venv/bin/activate"
echo "  PYTHONPATH=\$(pwd) python3 test_phase1.py"
echo ""
echo "Run the simulation as prosumer:"
echo "  source venv/bin/activate"
echo "  PYTHONPATH=\$(pwd) python3 core/main.py --mock --device pi1"
echo ""
echo "Run the simulation as consumer:"
echo "  source venv/bin/activate"
echo "  PYTHONPATH=\$(pwd) python3 core/main.py --mock --device pi2"
