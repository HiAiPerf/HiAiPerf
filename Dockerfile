# Use a lightweight Python base image
# Changed from 3.10 to 3.12
FROM python:3.12-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for ffmpeg and audio processing
# This ensures pydub and ffmpeg-python can function correctly.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code from the 'src' directory into a 'src' directory inside the container's /app
COPY src/ ./src/

# Expose the port that Gradio runs on
EXPOSE 7860

# Command to run the Gradio application, now located in the 'src' subdirectory
CMD ["python", "src/app_gradio.py"]
