# --------------------- Base Image ---------------------
FROM python:3.10-slim

# --------------------- Set Workdir ---------------------
WORKDIR /app

# --------------------- Install System Dependencies ---------------------
RUN apt-get update && \
    apt-get install -y gcc g++ build-essential git && \
    rm -rf /var/lib/apt/lists/*

# --------------------- Copy Files ---------------------
COPY . .

# --------------------- Upgrade pip & Install Python Packages ---------------------
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# --------------------- Expose Port ---------------------
EXPOSE 8080

# --------------------- Start Bot ---------------------
CMD ["python", "main.py"]
