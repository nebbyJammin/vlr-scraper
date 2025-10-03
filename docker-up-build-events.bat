@echo off
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.build-events.yml up -d --build