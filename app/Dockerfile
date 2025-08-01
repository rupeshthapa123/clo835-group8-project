FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev mysql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy application files
COPY . /app
WORKDIR /app

# Create necessary directories
RUN mkdir -p images

# Upgrade pip and install Python dependencies
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# Expose the application port
EXPOSE 81

# Set the entry point and command
ENTRYPOINT ["python3"]
CMD ["app.py"]