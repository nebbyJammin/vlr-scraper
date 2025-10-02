# Use an official Python image as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Prevent Python from writing pyc files and enable stoud/stderr buffering
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the requirements and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Install autossh and ssh
RUN apt-get update && apt-get install -y \
    autossh \
    openssh-client \
    dos2unix \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy ssh keys (for prod or mount via volume in dev)
COPY .ssh/id_ed25519 /root/.ssh/id_ed25519
COPY .ssh/known_hosts /root/.ssh/known_hosts

RUN dos2unix /root/.ssh/id_ed25519
RUN chmod 600 /root/.ssh/id_ed25519

RUN chmod 700 /root/.ssh

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["./start.sh"]