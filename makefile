.PHONY: help generate-config validate doctor up down restart logs ps health test clean shell

RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
NC=\033[0m

help:
	@echo "${GREEN}LiteLLM Proxy Commands${NC}"
	@echo ""
	@echo "  ${YELLOW}Core:${NC}"
	@echo "    make up              - Start LiteLLM proxy"
	@echo "    make down            - Stop LiteLLM proxy"
	@echo "    make restart         - Restart LiteLLM proxy"
	@echo "    make logs            - View logs (last 100 lines)"
	@echo "    make ps              - Show container status"
	@echo "    make health          - Check health"
	@echo ""
	@echo "  ${YELLOW}Configuration:${NC}"
	@echo "    make generate-config  - Generate config from providers.yml"
	@echo "    make validate         - Validate config for errors"
	@echo "    make doctor           - Run diagnostics"
	@echo ""
	@echo "  ${YELLOW}Testing:${NC}"
	@echo "    make test             - Run smoke test against API"
	@echo ""
	@echo "  ${YELLOW}Maintenance:${NC}"
	@echo "    make clean            - Remove containers and volumes"

generate-config:
	@echo "${GREEN}Generating config from providers.yml...${NC}"
	@python3 scripts/generate_config.py

validate:
	@echo "${GREEN}Validating configuration...${NC}"
	@python3 scripts/validate_config.py config/litellm/config.yml

doctor:
	@echo "${GREEN}Running diagnostics...${NC}"
	@python3 scripts/doctor.py

up:
	@echo "${GREEN}Running diagnostics...${NC}"
	@python3 scripts/doctor.py --preflight
	@echo ""
	@echo "${GREEN}Generating config...${NC}"
	@python3 scripts/generate_config.py
	@echo ""
	@echo "${GREEN}Validating config...${NC}"
	@python3 scripts/validate_config.py config/litellm/config.yml
	@echo ""
	@echo "${GREEN}Starting LiteLLM proxy...${NC}"
	docker compose up -d
	@echo "${GREEN}Waiting for LiteLLM to be ready...${NC}"
	@for i in $$(seq 1 30); do \
		if curl -sf http://localhost:4000/health/readiness >/dev/null 2>&1; then \
			echo "${GREEN}LiteLLM is ready${NC}"; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "${RED}LiteLLM failed to start within 30s${NC}"; \
	docker compose logs --tail=50 litellm; \
	exit 1

down:
	@echo "${YELLOW}Stopping LiteLLM proxy...${NC}"
	docker compose down

restart:
	@echo "${GREEN}Running diagnostics...${NC}"
	@python3 scripts/doctor.py --preflight
	@echo ""
	@echo "${GREEN}Generating config...${NC}"
	@python3 scripts/generate_config.py
	@echo ""
	@echo "${GREEN}Validating config...${NC}"
	@python3 scripts/validate_config.py config/litellm/config.yml
	@echo ""
	@echo "${YELLOW}Recreating LiteLLM proxy...${NC}"
	docker compose up -d --force-recreate
	@echo "${GREEN}Waiting for LiteLLM to be ready...${NC}"
	@for i in $$(seq 1 30); do \
		if curl -sf http://localhost:4000/health/readiness >/dev/null 2>&1; then \
			echo "${GREEN}LiteLLM is ready${NC}"; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "${RED}LiteLLM failed to start within 30s${NC}"; \
	docker compose logs --tail=50 litellm; \
	exit 1

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

health:
	@echo "${GREEN}Checking service health...${NC}"
	@./scripts/healthcheck.sh

test:
	@echo "${GREEN}Running smoke test...${NC}"
	@python3 test_api.py

clean:
	@echo "${RED}WARNING: This will delete all containers and volumes!${NC}"
	@echo "${RED}Type 'yes' to confirm:${NC} " && read ans && [ "$$ans" = "yes" ]
	docker compose down -v --remove-orphans
	@echo "${RED}All containers and volumes removed${NC}"

shell:
	docker exec -it litellm-proxy /bin/sh
