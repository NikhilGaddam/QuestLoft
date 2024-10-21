# Use the official Python image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

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

# Command to run the app with Gunicorn
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT} --workers=3 --timeout=120 main:app"]
