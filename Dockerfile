# ------------------- Base Image -------------------
FROM python:3.10-slim

# ------------------- Environment Variables -------------------
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# ------------------- Set Working Directory -------------------
WORKDIR /app

# ------------------- Copy Project Files -------------------
COPY . /app

# ------------------- Install Dependencies -------------------
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ------------------- Expose Port for Health Check -------------------
EXPOSE 8080

# ------------------- Run the Bot -------------------
CMD ["python", "main.py"]
