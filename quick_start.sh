#!/bin/bash
# Quick Start Script for Sora Video Generator

echo "==================================="
echo "Sora Video Generator - Quick Start"
echo "==================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Setting up .env file..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env and add your OpenAI API key"
    echo "   Then run this script again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Check for API key
if grep -q "sk-your-api-key-here" .env; then
    echo "⚠️  WARNING: Please update your API key in .env file"
    echo "   Current key appears to be the example placeholder"
    echo ""
fi

echo "==================================="
echo "Setup complete! Ready to generate videos."
echo "==================================="
echo ""
echo "Quick commands:"
echo ""
echo "1. Generate a single video:"
echo "   python sora_video_generator.py --prompt 'A sunset over the ocean' --duration 10"
echo ""
echo "2. Generate from example prompts:"
echo "   python sora_video_generator.py --prompts-file example_prompts.txt --duration 10"
echo ""
echo "3. Custom prompts file:"
echo "   python sora_video_generator.py --prompts-file your_prompts.txt --duration 10 --model standard"
echo ""
echo "For more options, see README.md or run:"
echo "   python sora_video_generator.py --help"
echo ""
