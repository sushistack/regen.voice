# Use the official ROCm PyTorch image as the base
FROM rocm/pytorch:latest

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install system dependencies that might be needed. ffmpeg is often required for audio processing.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Install the Python dependencies from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project's scripts directory into the container so they can be executed
COPY ./scripts /app/scripts
