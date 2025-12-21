# Use the official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED True
ENV APP_HOME /app
ENV OLLAMA_HOST "http://127.0.0.1:11434"

# Install system dependencies & Ollama
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://ollama.com/install.sh | sh

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose the port Gunicorn will run on
EXPOSE 8080

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
