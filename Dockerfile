# Python slim base for small image.
FROM python:3.11-slim

# Prevent Python from writing .pyc and enable unbuffered logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENAI_MODEL=gpt-4.1

# Workdir.
WORKDIR /app

# Install app dependencies first for better layer caching.
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy source.
COPY app /app/app

# Create non-root user and switch.
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose service port.
EXPOSE 8000

# Container-level healthcheck using script.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python /app/app/healthcheck.py || exit 1

# Start the API.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
