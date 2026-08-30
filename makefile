.PHONY: help up down restart logs ps status health validate test clean backup

RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
NC=\033[0m

help:
	@echo "${GREEN}LiteLLM Proxy Commands${NC}"
	@echo ""
	@echo "  ${YELLOW}Core Runtime:${NC}"
	@echo "    make up              - Start core services (LiteLLM only, minimal RAM)"
	@echo "    make down            - Stop all services"
	@echo "    make restart         - Restart core services"
	@echo "    make logs            - View logs (last 100 lines)"
	@echo "    make ps              - Show container status"
	@echo "    make health          - Check health of running services"
	@echo ""
	@echo "  ${YELLOW}Optional Profiles:${NC}"
	@echo "    make up-cache        - Start with Redis cache"
	@echo "    make up-database     - Start with PostgreSQL"
	@echo "    make up-monitoring   - Start with Prometheus/Grafana"
	@echo "    make up-full         - Start all services"
	@echo "    make down-monitoring - Stop monitoring services"
	@echo ""
	@echo "  ${YELLOW}Validation & Testing:${NC}"
	@echo "    make validate        - Validate config for errors"
	@echo "    make test            - Run smoke test against API"
	@echo ""
	@echo "  ${YELLOW}Maintenance:${NC}"
	@echo "    make backup          - Backup config and databases"
	@echo "    make clean           - Remove all volumes (DESTRUCTIVE)"

up:
	@echo "${GREEN}Starting core services (minimal mode)...${NC}"
	docker compose up -d
	@echo "${GREEN}Waiting for LiteLLM to be ready...${NC}"
	@sleep 5
	@make health

up-cache:
	@echo "${GREEN}Starting with Redis cache...${NC}"
	docker compose --profile cache up -d
	@sleep 5
	@make health

up-database:
	@echo "${GREEN}Starting with PostgreSQL database...${NC}"
	docker compose --profile database up -d
	@sleep 5
	@make health

up-monitoring:
	@echo "${GREEN}Starting monitoring services...${NC}"
	docker compose --profile monitoring up -d
	@sleep 5
	@make health

up-full:
	@echo "${GREEN}Starting all services...${NC}"
	docker compose --profile cache --profile database --profile monitoring up -d
	@sleep 10
	@make health

down:
	@echo "${YELLOW}Stopping all services...${NC}"
	docker compose down

down-monitoring:
	@echo "${YELLOW}Stopping monitoring services...${NC}"
	docker compose --profile monitoring down

restart:
	@echo "${YELLOW}Restarting core services...${NC}"
	docker compose restart

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

health:
	@echo "${GREEN}Checking service health...${NC}"
	@./scripts/healthcheck.sh

validate:
	@echo "${GREEN}Validating configuration...${NC}"
	@python3 scripts/validate_config.py config/litellm/config.yml

test:
	@echo "${GREEN}Running smoke test...${NC}"
	@python3 test_api.py

backup:
	@echo "${GREEN}Creating backup...${NC}"
	@./scripts/backup.sh

clean:
	@echo "${RED}WARNING: This will delete all volumes and data!${NC}"
	@echo "${RED}Type 'yes' to confirm:${NC} " && read ans && [ "$$ans" = "yes" ]
	docker compose down -v
	@echo "${RED}All volumes removed${NC}"

shell-litellm:
	docker exec -it litellm-proxy /bin/sh

shell-redis:
	docker exec -it litellm-redis redis-cli -a "${REDIS_PASSWORD}"

shell-postgres:
	docker exec -it litellm-postgres psql -U "${POSTGRES_USER:-litellm}" -d "${POSTGRES_DB:-litellm}"
