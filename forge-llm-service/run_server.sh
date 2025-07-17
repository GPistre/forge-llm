#!/bin/bash

# Check if the virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. OpenAI API key may be missing."
    echo "Creating example .env file..."
    echo "OPENAI_API_KEY=your_api_key_here" > .env
    echo "PORT=7861" >> .env
    echo "Please edit the .env file to add your OpenAI API key."
fi

# Start the server
echo "Starting LLM server..."
python3 test_server.py