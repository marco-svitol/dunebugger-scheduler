# Use Python 3.11 slim image as base (Debian Bookworm)
FROM python:3.11-slim-bookworm AS builder

ARG APP_UID=1000
ARG APP_GID=1000

# Set working directory for build stage
WORKDIR /build

# Copy only what's needed to extract version
COPY .git/ ./.git/
COPY generate_version.sh ./

# Extract version information from git and generate version file
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    chmod +x generate_version.sh && \
    ./generate_version.sh && \
    apt-get remove -y git && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Final stage - minimal runtime image
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

# Install Python dependencies and git (needed for version.py to read git tags)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy generated version file from builder stage
COPY --from=builder /build/VERSION ./VERSION

# Copy application code
COPY app/ ./app/

RUN groupadd -g ${APP_GID} appuser \
 && useradd  -u ${APP_UID} -g ${APP_GID} -r -m appuser

RUN chown -R appuser:appuser /app
USER appuser

# Set the entrypoint
WORKDIR /app/app
CMD ["python", "main.py"]