#!/bin/bash

echo "🔧 Setting up your Stock Analyzer project..."

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtualenv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "📥 Installing required packages..."
pip install -r requirements.txt

echo "✅ All dependencies installed!"