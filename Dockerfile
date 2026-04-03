# Build a production-ready persona image
FROM python:3.9-slim

# Install system dependencies for high-performance libraries (pandas, pyarrow)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies before copying code to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application modules
COPY core/ core/
COPY gateway/ gateway/
COPY workers/ workers/
COPY frontend/ frontend/

# Ensure all packages are discoverable
ENV PYTHONPATH=/app

# Default command for the base image (will be overridden in docker-compose.yaml)
CMD ["python3", "-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
