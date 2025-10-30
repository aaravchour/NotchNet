#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Download the index from GCS
# The GCS_INDEX_PATH env var will be set in Cloud Run
# e.g., gs://your-bucket-name/faiss_index.tar.gz
echo "Downloading FAISS index from ${GCS_INDEX_PATH}..."
gsutil cp "${GCS_INDEX_PATH}" /app/faiss_index.tar.gz

# Decompress the index
echo "Decompressing index..."
tar -xzf /app/faiss_index.tar.gz -C /app
echo "Index decompressed to /app/faiss_index"

# Start the Gunicorn server
# It will listen on the port specified by the $PORT environment variable,
# which is automatically set by Cloud Run.
echo "Starting Gunicorn server..."
gunicorn --bind :${PORT} --workers 1 --threads 8 --timeout 0 server:app