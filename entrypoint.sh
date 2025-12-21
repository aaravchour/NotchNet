#!/bin/bash

# Start Ollama server in the background
ollama serve & 

# Wait for Ollama to be ready
while ! ollama list > /dev/null 2>&1; do
  echo "Waiting for Ollama server to start..."
  sleep 1
done

# Pull the required models
ollama pull mxbai-embed-large
ollama pull deepseek-v3.1:671b-cloud

# Start the web server
gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 8 --timeout 0 server:app
