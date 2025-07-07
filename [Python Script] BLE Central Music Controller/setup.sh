#!/bin/bash

echo "Creating python virtual environment"
python3 -m venv venv

echo "Activating virtual environment"
source venv/bin/activate

echo "upgrade pip"
pip install --upgrade pip

echo "python packages..."
pip install bleak pyyaml

echo "setup complete"
echo "To activate the virtual environment, run:"
echo "source venv/bin/activate"
