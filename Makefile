# AI Error Solver Backend - Makefile
.PHONY: help build run stop logs clean test docker-build docker-push deploy infra-up infra-down setup

# Variables
IMAGE_NAME := bayajid23/ai-error-solver-backend
CONTAINER_NAME := ai-error-solver
DOCKER_REPO := bayajid23/ai-error-solver-backend

# Default target
help: ## Show this help message
	@echo "AI Error Solver Backend - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Commands
install: ## Install dependencies using uv
	uv sync

run: ## Run the application locally
	uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

test: ## Run tests
	uv run pytest app/tests/ -v

lint: ## Run linting
	uv run ruff check .
	uv run ruff format --check .

format: ## Format code
	uv run ruff format .

# Docker Commands
docker-build: ## Build Docker image
	docker build -t $(IMAGE_NAME):latest .

docker-run: ## Run Docker container locally
	docker run -d \
		--name $(CONTAINER_NAME) \
		-p 8000:8000 \
		--env-file .env \
		$(IMAGE_NAME):latest

docker-stop: ## Stop Docker container
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

docker-logs: ## Show Docker container logs
	docker logs -f $(CONTAINER_NAME)

docker-push: ## Push Docker image to registry
	docker push $(IMAGE_NAME):latest

docker-pull: ## Pull Docker image from registry
	docker pull $(IMAGE_NAME):latest

# Infrastructure Commands
infra-setup: ## Setup Pulumi infrastructure dependencies
	cd infra && npm install

infra-up: ## Deploy infrastructure using Pulumi
	cd infra && pulumi up --yes

infra-down: ## Destroy infrastructure using Pulumi
	cd infra && pulumi down --yes

infra-preview: ## Preview infrastructure changes
	cd infra && pulumi preview

infra-config: ## Configure Pulumi stack
	cd infra && pulumi config set aws:region us-east-1
	cd infra && pulumi config set instanceType t3.micro

# Database Commands
db-create: ## Create database
	uv run python create_db.py

db-migrate: ## Run database migrations
	@echo "Add your migration command here"

# Deployment Commands
deploy-local: docker-build docker-stop docker-run ## Deploy locally using Docker

deploy-staging: ## Deploy to staging environment
	@echo "Staging deployment - push to staging branch to trigger GitHub Actions"

deploy-prod: ## Deploy to production environment
	@echo "Production deployment - push to main branch to trigger GitHub Actions"

# Utility Commands
clean: ## Clean up Docker images and containers
	docker system prune -f
	docker image prune -f

logs: ## Show application logs
	tail -f /var/log/ai-error-solver/app.log || echo "No logs found"

health: ## Check application health
	curl -f http://localhost:8000/health || echo "Application not responding"

# Setup Commands
setup-dev: ## Setup development environment
	uv sync
	cp .env.example .env || echo "Create .env file with required variables"
	@echo "Development environment setup complete!"

setup-infra: ## Setup infrastructure environment
	cd infra && npm install
	cd infra && pulumi login
	cd infra && pulumi stack init dev || echo "Stack already exists"
	@echo "Infrastructure environment setup complete!"

setup-all: setup-dev setup-infra ## Setup complete development and infrastructure environment

# GitHub Repository Commands
create-dockerhub-repo: ## Instructions to create DockerHub repository
	@echo "1. Go to https://hub.docker.com"
	@echo "2. Click 'Create Repository'"
	@echo "3. Repository name: ai-error-solver-backend"
	@echo "4. Make it public"
	@echo "5. Create repository"

github-secrets: ## Instructions to setup GitHub secrets
	@echo "Add these secrets to your GitHub repository settings:"
	@echo ""
	@echo "Docker Secrets:"
	@echo "  DOCKERHUB_USERNAME: bayajid23"
	@echo "  DOCKERHUB_TOKEN: <your-dockerhub-token>"
	@echo ""
	@echo "AWS Secrets:"
	@echo "  AWS_ACCESS_KEY_ID: <your-aws-access-key>"
	@echo "  AWS_SECRET_ACCESS_KEY: <your-aws-secret-key>"
	@echo ""
	@echo "Application Secrets:"
	@echo "  DATABASE_URL: <your-database-url>"
	@echo "  GEMINI_API_KEY: <your-gemini-api-key>"
	@echo "  VOYAGE_API_KEY: <your-voyage-api-key>"
	@echo "  JWT_SECRET_KEY: <your-jwt-secret>"
	@echo "  QDRANT_HOST: <your-qdrant-host>"
	@echo "  QDRANT_PORT: <your-qdrant-port>"
	@echo "  QDRANT_API_KEY: <your-qdrant-api-key>"
	@echo ""
	@echo "EC2 Secrets (will be available after infra deployment):"
	@echo "  EC2_PUBLIC_IP: <ec2-public-ip>"
	@echo "  EC2_SSH_KEY: <private-key-content>"

# Environment file template
env-template: ## Create .env template file
	@echo "Creating .env.example template..."
	@cat > .env.example << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/ai_error_solver

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
VOYAGE_API_KEY=your_voyage_api_key_here

# JWT Configuration
JWT_SECRET_KEY=your_super_secret_jwt_key_here

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your_qdrant_api_key_here
EOF
	@echo ".env.example created! Copy it to .env and fill in your values."
