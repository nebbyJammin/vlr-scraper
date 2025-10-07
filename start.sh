#!/bin/sh

# Start autossh in background if keys are present
if [ -f /root/.ssh/id_ed25519 ]; then
    echo "Starting autossh..."
    mkdir -p logs/autossh/
    autossh -M 0 -N -f -o StrictHostKeyChecking=no -i /root/.ssh/id_ed25519 -L $LOCAL_PORT:$API_HOST:$API_PORT $SSH_USER@$SSH_HOST >> /app/logs/autossh/autossh.log 2>&1
fi

while ! nc -z localhost 8111; do
    echo "Waiting for SSH tunnel..."
    sleep 1
done

exec python main.py $FLAGS