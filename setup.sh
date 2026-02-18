#!/bin/bash

# Exit on any error
set -e

echo "=== Setting up benchmarking environment ==="

# Install system dependencies
echo "Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip fping iperf3 traceroute net-tools ethtool
elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf install -y python3 python3-pip fping iperf3 traceroute net-tools ethtool
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y python3 python3-pip fping iperf3 traceroute net-tools ethtool
elif command -v pacman &> /dev/null; then
    # Arch Linux
    sudo pacman -S --noconfirm python python-pip fping iperf3 traceroute net-tools ethtool
else
    echo "Unsupported package manager. Please install python3, python3-venv, and python3-pip manually."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "=== Setup complete! ==="
echo "To activate the virtual environment in the future, run:"
echo "  source .venv/bin/activate"
