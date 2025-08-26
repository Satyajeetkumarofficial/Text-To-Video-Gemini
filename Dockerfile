# Step 1: Base image
FROM python:3.10-slim

# Step 2: Set work directory
WORKDIR /app

# Step 3: Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Step 4: Copy project files
COPY requirements.txt .
COPY main.py .
COPY .env .

# Step 5: Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: Expose port (Koyeb uses 8080)
EXPOSE 8080

# Step 7: Run the bot
CMD ["python", "main.py"]
