# GHL Sales Assistant Backend
# Usage:
#   docker build -t ghl-assistant-api .
#   docker run -p 8000:8000 --env-file .env ghl-assistant-api

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
