#!/bin/bash
# Setup script for Website Spell Checker

echo "Setting up Website Spell Checker..."
echo "=================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

echo "Python 3 found: $(python3 --version)"

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "Dependencies installed successfully!"
else
    echo "Error installing dependencies. Please check your Python/pip installation."
    exit 1
fi

# Make the main script executable
chmod +x website_spellcheck.py

echo ""
echo "Setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your website URL"
echo "2. Add custom terms to the dictionaries/ folder"
echo "3. Run: python3 website_spellcheck.py https://your-website.com"
echo ""
echo "For more information, see README.md"