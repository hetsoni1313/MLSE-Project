#!/bin/bash
# Setup script for the LLMOps Governance Platform
set -e

echo "🚀 Setting up LLMOps Governance Platform..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/{raw,processed,splits,manifests}
mkdir -p artifacts
mkdir -p experiments/{results,runs}
mkdir -p ~/.cache/llmops-governance/models

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

echo "📥 Downloading Banking77 dataset..."
python scripts/download_data.py

echo "📊 Preparing data splits..."
python scripts/prepare_data.py

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Start gateway: make run-gateway"
echo "  3. Start dashboard: make run-dashboard"
echo "  4. Run tests: make test"

