FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ENV MONGO_URI=YOUR_MONGO_URI
ENV ADMIN_ID=123456789

CMD ["python", "bot.py"]
