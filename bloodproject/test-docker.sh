#!/bin/bash

# Test Docker build locally
echo "Testing Docker build..."

# Build the image
docker build -t blood-analysis-app .

# Run the container locally
echo "Running container locally..."
docker run -p 8000:8080 \
    -e DEBUG=True \
    -e DB_HOST=host.docker.internal \
    -e DB_NAME=blooddb \
    -e DB_USER=postgres \
    -e DB_PASSWORD=jOHNcENA123! \
    blood-analysis-app

echo "Container stopped."
