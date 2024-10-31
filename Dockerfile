# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install Redis and other necessary dependencies
RUN apt-get update && \
    apt-get install -y redis-server && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the required Python packages
RUN pip install --no-cache-dir Flask Flask-Cors opencv-python-headless redis

# Expose ports for the Flask app, socket server, and Redis
EXPOSE 5000 8000 6379

# Command to start both Redis server and Flask app
CMD service redis-server start && python application.py
