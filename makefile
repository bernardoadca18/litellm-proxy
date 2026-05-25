.PHONY: help up down logs clean backup rotate-keys

# Cores para output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
NC=\033[0m # No Color

help:
	@echo "${GREEN}LiteLLM Proxy Commands${NC}"
	@echo "  ${YELLOW}make up${NC}         - Start all services"
	@echo "  ${YELLOW}make down${NC}       - Stop all services"
	@echo "  ${YELLOW}make logs${NC}       - View logs"
	@echo "  ${YELLOW}make status${NC}     - Check service status"
	@echo "  ${YELLOW}make backup${NC}     - Backup databases"
	@echo "  ${YELLOW}make clean${NC}      - Remove volumes (danger!)"
	@echo "  ${YELLOW}make rotate-keys${NC}- Rotate API keys"
	@echo "  ${YELLOW}make health${NC}     - Check health endpoints"

up:
	@echo "${GREEN}Starting services...${NC}"
	docker compose up -d
	@echo "${GREEN}Waiting for services to be ready...${NC}"
	sleep 10
	make health

down:
	@echo "${YELLOW}Stopping services...${NC}"
	docker compose down

logs:
	docker compose logs -f --tail=100

status:
	docker compose ps

health:
	@echo "${GREEN}Checking health...${NC}"
	@curl -s http://localhost:4000/health | jq . || echo "LiteLLM not ready"
	@curl -s http://localhost:9090/-/healthy | jq . || echo "Prometheus not ready"
	@curl -s http://localhost:3000/api/health | jq . || echo "Grafana not ready"

backup:
	@echo "${GREEN}Creating backup...${NC}"
	mkdir -p backups
	docker exec litellm-postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backups/postgres_$$(date +%Y%m%d_%H%M%S).sql
	docker exec litellm-redis redis-cli --pass ${REDIS_PASSWORD} SAVE
	@echo "${GREEN}Backup complete${NC}"

clean:
	@echo "${RED}This will delete all volumes! Are you sure? [y/N]${NC}" && read ans && [ $${ans:-N} = y ]
	docker-compose down -v
	@echo "${RED}Volumes removed${NC}"

rotate-keys:
	@echo "${YELLOW}Rotating API keys...${NC}"
	@./scripts/rotate-keys.sh

shell-litellm:
	docker exec -it litellm-proxy /bin/sh

shell-postgres:
	@export $(grep -v '^#' .env | xargs) && docker exec -it litellm-postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB

shell-redis:
	docker exec -it litellm-redis redis-cli -a ${REDIS_PASSWORD}
