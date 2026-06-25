FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for compiling standard libraries and curl for health check
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python library dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all workspace project files
COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Add container health check to verify Streamlit application is running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Launch the Streamlit application
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
