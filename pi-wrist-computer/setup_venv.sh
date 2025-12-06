#!/bin/bash
# Setup virtual environment for Pi Wrist Computer

echo "Setting up virtual environment..."

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo "Installing Python packages..."
pip install -r requirements.txt

echo ""
echo "Virtual environment setup complete!"
echo ""
echo "To use it, run:"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo ""
echo "Or use the run script: ./run.sh"

