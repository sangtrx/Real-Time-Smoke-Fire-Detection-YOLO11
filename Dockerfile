# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/logs /app/detected_fires

# Copy only necessary files
COPY requirements.txt .
COPY src/ src/
COPY models/best_nano_111.pt models/best_nano_111.pt
COPY data/ data/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create startup script
RUN echo '#!/bin/bash\n\
    trap "exit" SIGINT SIGTERM\n\
    python src/bot.py & \n\
    BOT_PID=$!\n\
    python src/main.py & \n\
    MAIN_PID=$!\n\
    wait $BOT_PID $MAIN_PID\n\
    ' > /app/start.sh && chmod +x /app/start.sh

# Command to run both processes
CMD ["/app/start.sh"]