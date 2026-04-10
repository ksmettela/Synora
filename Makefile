.PHONY: help up down build logs test init clean sdk-build sdk-build-android \
        test-fingerprint-ingestor test-advertiser-api test-privacy-service \
        ps status shell-postgres shell-kafka restart-services lint format

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

DOCKER_COMPOSE := docker-compose
DOCKER := docker

help:
	@echo "$(BLUE)Synora Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Infrastructure:$(NC)"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make build           - Build service images"
	@echo "  make rebuild         - Rebuild all images (no cache)"
	@echo "  make ps              - Show running services"
	@echo "  make status          - Show detailed service status"
	@echo "  make logs            - Tail logs for all services"
	@echo "  make init            - Initialize databases and Kafka topics"
	@echo "  make clean           - Stop all services and remove volumes"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make test            - Run all tests"
	@echo "  make test-coverage   - Run tests with coverage"
	@echo "  make lint            - Lint all services"
	@echo "  make format          - Format code (Go, Python)"
	@echo ""
	@echo "$(GREEN)SDK Building:$(NC)"
	@echo "  make sdk-build       - Build C++ SDK"
	@echo "  make sdk-build-android - Build Android SDK"
	@echo ""
	@echo "$(GREEN)Debugging:$(NC)"
	@echo "  make shell-postgres  - Connect to PostgreSQL shell"
	@echo "  make shell-kafka     - Connect to Kafka container"
	@echo "  make restart-services - Restart all services"
	@echo ""

up:
	@echo "$(GREEN)Starting Synora services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@sleep 5
	@echo "$(GREEN)✓ Services started. Waiting for health checks...$(NC)"
	@$(DOCKER_COMPOSE) ps

down:
	@echo "$(RED)Stopping Synora services...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Services stopped$(NC)"

build:
	@echo "$(GREEN)Building service images...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Build complete$(NC)"

rebuild:
	@echo "$(GREEN)Rebuilding all images (no cache)...$(NC)"
	$(DOCKER_COMPOSE) build --no-cache
	@echo "$(GREEN)✓ Build complete$(NC)"

ps:
	@echo "$(BLUE)Running Services:$(NC)"
	@$(DOCKER_COMPOSE) ps

status:
	@echo "$(BLUE)Detailed Service Status:$(NC)"
	@echo ""
	@for service in $$($(DOCKER_COMPOSE) config --services); do \
		status=$$($(DOCKER_COMPOSE) ps $$service | tail -1 | awk '{print $$NF}'); \
		echo "  $$service: $(GREEN)$$status$(NC)"; \
	done

logs:
	@echo "$(BLUE)Tailing logs for all services (Ctrl+C to exit)...$(NC)"
	$(DOCKER_COMPOSE) logs -f

logs-%:
	@echo "$(BLUE)Tailing logs for $*...$(NC)"
	$(DOCKER_COMPOSE) logs -f $*

init:
	@echo "$(GREEN)Initializing Synora infrastructure...$(NC)"
	@chmod +x docker-compose.init.sh
	@./docker-compose.init.sh

test:
	@echo "$(GREEN)Running all tests...$(NC)"
	@echo "$(BLUE)Testing Fingerprint Ingestor...$(NC)"
	cd services/fingerprint-ingestor && go test ./... -v
	@echo "$(BLUE)Testing Advertiser API...$(NC)"
	cd services/advertiser-api && python -m pytest tests/ -v
	@echo "$(BLUE)Testing Privacy Service...$(NC)"
	cd services/privacy-service && python -m pytest tests/ -v
	@echo "$(BLUE)Testing Billing Service...$(NC)"
	cd services/billing-service && python -m pytest tests/ -v
	@echo "$(GREEN)✓ All tests passed$(NC)"

test-coverage:
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	@mkdir -p coverage
	@echo "$(BLUE)Coverage: Fingerprint Ingestor...$(NC)"
	cd services/fingerprint-ingestor && go test ./... -cover -coverprofile=../../coverage/fingerprint-ingestor.out
	@echo "$(BLUE)Coverage: Advertiser API...$(NC)"
	cd services/advertiser-api && python -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=html:../../coverage/advertiser-api
	@echo "$(BLUE)Coverage: Privacy Service...$(NC)"
	cd services/privacy-service && python -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=html:../../coverage/privacy-service
	@echo "$(GREEN)✓ Coverage reports generated in ./coverage/$(NC)"

test-fingerprint-ingestor:
	@echo "$(BLUE)Testing Fingerprint Ingestor...$(NC)"
	cd services/fingerprint-ingestor && go test ./... -v

test-advertiser-api:
	@echo "$(BLUE)Testing Advertiser API...$(NC)"
	cd services/advertiser-api && python -m pytest tests/ -v

test-privacy-service:
	@echo "$(BLUE)Testing Privacy Service...$(NC)"
	cd services/privacy-service && python -m pytest tests/ -v

lint:
	@echo "$(GREEN)Linting codebase...$(NC)"
	@echo "$(BLUE)Linting Go services...$(NC)"
	cd services/fingerprint-ingestor && golangci-lint run ./...
	@echo "$(BLUE)Linting Python services...$(NC)"
	cd services/advertiser-api && pylint app/ || true
	cd services/privacy-service && pylint app/ || true
	cd services/billing-service && pylint app/ || true
	cd services/matching-engine && pylint . || true
	@echo "$(GREEN)✓ Linting complete$(NC)"

format:
	@echo "$(GREEN)Formatting codebase...$(NC)"
	@echo "$(BLUE)Formatting Go code...$(NC)"
	cd services/fingerprint-ingestor && gofmt -s -w .
	@echo "$(BLUE)Formatting Python code...$(NC)"
	cd services/advertiser-api && black . && isort .
	cd services/privacy-service && black . && isort .
	cd services/billing-service && black . && isort .
	cd services/matching-engine && black . && isort .
	@echo "$(GREEN)✓ Formatting complete$(NC)"

sdk-build:
	@echo "$(GREEN)Building C++ SDK...$(NC)"
	cd sdk && mkdir -p build && cd build && cmake .. && make -j$$(nproc)
	@echo "$(GREEN)✓ SDK built successfully$(NC)"

sdk-build-android:
	@echo "$(GREEN)Building Android SDK...$(NC)"
	@if [ ! -d "$$ANDROID_HOME" ]; then \
		echo "$(RED)Error: ANDROID_HOME not set$(NC)"; \
		exit 1; \
	fi
	cd sdk/android && ./gradlew build
	@echo "$(GREEN)✓ Android SDK built successfully$(NC)"

shell-postgres:
	@echo "$(BLUE)Connecting to PostgreSQL...$(NC)"
	$(DOCKER) exec -it acraas-postgres psql -U acraas -d acraas

shell-kafka:
	@echo "$(BLUE)Connecting to Kafka container...$(NC)"
	$(DOCKER) exec -it acraas-kafka bash

restart-services:
	@echo "$(YELLOW)Restarting all services...$(NC)"
	$(DOCKER_COMPOSE) restart
	@sleep 3
	@$(DOCKER_COMPOSE) ps

clean:
	@echo "$(RED)Cleaning up all containers and volumes...$(NC)"
	$(DOCKER_COMPOSE) down -v
	@rm -rf coverage/
	@echo "$(GREEN)✓ Clean complete$(NC)"

.DEFAULT_GOAL := help
