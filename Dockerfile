FROM python:3.12-slim

# Install aria2c
RUN apt-get update && \
    apt-get install -y aria2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /downloads /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "scripts.run_dispatcher"] 