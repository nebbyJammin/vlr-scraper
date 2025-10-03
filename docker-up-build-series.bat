@echo off
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.build-series.yml up -d --build