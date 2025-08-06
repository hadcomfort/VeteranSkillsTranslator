# ==============================================================================
#  Dockerfile for Military Skills Translator
# ==============================================================================
#
#  This file defines the environment and steps required to build the Docker
#  image for the application.
#
#  Best Practices Used:
#  - Multi-stage builds are not necessary here but are a good practice for
#    compiled languages to keep the final image small.
#  - Using an official, slim Python base image.
#  - Caching dependencies by copying and installing requirements separately.
#  - Running as a non-root user for improved security.
#  - Using a production-grade WSGI server (Gunicorn) instead of the Flask
#    development server.
#
# ==============================================================================

# --- Stage 1: Build ---
# Use an official Python runtime as a parent image. 'slim-buster' is a good
# balance between size and functionality.
FROM python:3.9-slim-buster

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies first.
# This leverages Docker's layer caching. The dependencies will only be
# re-installed if the requirements.txt file changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code into the container
COPY . .

# Create a non-root user and switch to it for security reasons.
# Running processes as a non-root user is a critical security best practice.
RUN useradd --create-home appuser
USER appuser

# Expose the port that Gunicorn will run on.
EXPOSE 5000

# The command to run the application using Gunicorn.
# -w 4: Specifies 4 worker processes. A good starting point is (2 * CPU cores) + 1.
# -b 0.0.0.0:5000: Binds the server to all network interfaces on port 5000.
# app:app: Tells Gunicorn to run the 'app' object from the 'app.py' module.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
