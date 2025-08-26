# Base image
FROM python:3.10-slim

# Install build tools for tgcrypto
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    build-essential \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for health check
EXPOSE 8080

# Run the bot
CMD ["python", "main.py"]
