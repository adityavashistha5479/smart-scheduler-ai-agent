FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV DATABASE_URL=sqlite:///./production.db

# Expose port (Cloud Run defaults to 8080)
EXPOSE 8080

# Run FastAPI app with Uvicorn, binding to the PORT environment variable
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
