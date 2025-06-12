# GitHub Action Dockerfile for repo-file-sync
FROM python:3.13-slim

# Set metadata
LABEL maintainer="Studist Corporation"
LABEL description="Synchronize files from GitHub repositories with environment variable substitution"
LABEL version="2.0.0"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY entrypoint.sh ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Ensure entrypoint script is executable
RUN chmod +x entrypoint.sh

# Set environment variables for GitHub Actions
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Use entrypoint script with uv run
ENTRYPOINT ["/app/entrypoint.sh"]