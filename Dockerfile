# Use the official Python image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (Seems to be required only for windows)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app will run on
EXPOSE ${PORT}

# Set environment variables for Flask
ENV FLASK_APP=main.py
ENV FLASK_ENV=production


# The --reload flag can probably be removed for windows
# Command to run the app with Gunicorn
CMD ["sh", "-c", "python faiss-store.py && gunicorn -b 0.0.0.0:${PORT} --reload --workers=3 --timeout=120 main:app"]
