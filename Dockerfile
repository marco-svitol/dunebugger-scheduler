# Use Python 3.11 slim image as base (Debian Bookworm)
FROM python:3.11-slim-bookworm

ARG APP_UID=1000
ARG APP_GID=1000

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    #apt-get remove -y gcc python3-dev build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy application code
COPY app/ ./app/

RUN groupadd -g ${APP_GID} appuser \
 && useradd  -u ${APP_UID} -g ${APP_GID} -r -m appuser

RUN chown -R appuser:appuser /app
USER appuser

# Expose port (adjust if your app uses a specific port)
# EXPOSE 8000

# Set the entrypoint
WORKDIR /app/app
CMD ["python", "main.py"]