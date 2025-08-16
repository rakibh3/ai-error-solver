# AI Error Solver Backend - Complete Setup Guide

[![CI/CD Pipeline](https://github.com/rakibh3/ai-error-solver-backend/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/rakibh3/ai-error-solver-backend/actions/workflows/ci-cd.yml)

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Infrastructure Setup](#infrastructure-setup)
- [CI/CD Pipeline](#cicd-pipeline)
- [Local Development](#local-development)
- [Deployment](#deployment)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Commands Reference](#commands-reference)
- [Architecture](#architecture)

## 🎯 Overview

This is a FastAPI-based AI Error Solver Backend with a fully automated CI/CD pipeline. The system automatically:

1. **Builds** Docker images on code push
2. **Pushes** to DockerHub registry
3. **Deploys** to AWS EC2 instance
4. **Restarts** the application with zero downtime

### Tech Stack
- **Backend**: FastAPI, Python 3.12, SQLAlchemy, PostgreSQL
- **AI/ML**: Google Gemini API, Qdrant Vector Database, LangChain
- **Infrastructure**: AWS EC2, Pulumi (TypeScript)
- **CI/CD**: GitHub Actions, Docker, DockerHub
- **Deployment**: Automated Docker deployment

## 🔧 Prerequisites

### Required Accounts & Tools
1. **AWS Account** with CLI configured
2. **DockerHub Account** 
3. **GitHub Repository** with Actions enabled
4. **Pulumi Account** (free tier available)
5. **API Keys**: Gemini API, Voyage AI, Qdrant Cloud (optional)

### Required Software
```bash
# Install required tools
curl -fsSL https://get.pulumi.com | sh  # Pulumi CLI
pip install uv                          # UV package manager
docker --version                        # Docker Engine
aws --version                          # AWS CLI
```

## 🚀 Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/rakibh3/ai-error-solver-backend.git
cd ai-error-solver-backend

# Setup development environment
make setup-dev

# Create environment file
cp .env.example .env
# Edit .env with your API keys and database URL
```

### 2. Local Development
```bash
# Install dependencies
make install

# Run locally
make run

# Test the application
curl http://localhost:8000/health
curl http://localhost:8000/docs  # API documentation
```

### 3. Docker Testing
```bash
# Build and run with Docker
make docker-build
make deploy-local

# Check if running
make health
```

## 🏗️ Infrastructure Setup

### Step 1: AWS Preparation
```bash
# Configure AWS CLI
aws configure
# Enter your AWS Access Key ID, Secret, Region (ap-southeast-1), and output format

# Create EC2 Key Pair (required for SSH access)
aws ec2 create-key-pair --key-name ai-error-solver-key --query 'KeyMaterial' --output text > ~/.ssh/ai-error-solver-key.pem
chmod 600 ~/.ssh/ai-error-solver-key.pem
```

### Step 2: Pulumi Setup
```bash
# Setup infrastructure environment
make setup-infra

# Login to Pulumi (free account)
cd infra
pulumi login

# Initialize stack
pulumi stack init production

# Configure settings
pulumi config set aws:region ap-southeast-1
pulumi config set instanceType t3.micro
pulumi config set keyName ai-error-solver-key
```

### Step 3: Deploy Infrastructure
```bash
# Preview infrastructure changes
make infra-preview

# Deploy infrastructure
make infra-up

# Note down the outputs:
# - publicIp: Your EC2 public IP
# - appUrl: http://YOUR_EC2_IP:8000
# - sshCommand: SSH command to access EC2
```

### Step 4: DockerHub Setup
```bash
# Create DockerHub repository
# 1. Go to https://hub.docker.com
# 2. Click "Create Repository"
# 3. Repository name: ai-error-solver-backend
# 4. Make it public
# 5. Create repository

# Get DockerHub access token
# 1. Go to Account Settings > Security
# 2. Click "New Access Token"
# 3. Copy the token (you'll need this for GitHub secrets)
```

## 🔄 CI/CD Pipeline

### GitHub Secrets Configuration

Add these secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

#### Docker Secrets
```
DOCKERHUB_USERNAME: bayajid23
DOCKERHUB_TOKEN: your_dockerhub_access_token
```

#### AWS Secrets
```
AWS_ACCESS_KEY_ID: your_aws_access_key_id
AWS_SECRET_ACCESS_KEY: your_aws_secret_access_key
```

#### Application Secrets
```
DATABASE_URL: postgresql://username:password@host:5432/database
GEMINI_API_KEY: your_gemini_api_key
VOYAGE_API_KEY: your_voyage_api_key
JWT_SECRET_KEY: your_jwt_secret_key
QDRANT_HOST: your_qdrant_host
QDRANT_PORT: 6333
QDRANT_API_KEY: your_qdrant_api_key
```

#### EC2 Deployment Secrets
```
EC2_PUBLIC_IP: your_ec2_public_ip  # From Pulumi output
EC2_SSH_KEY: |
  -----BEGIN RSA PRIVATE KEY-----
  your_private_key_content_here
  -----END RSA PRIVATE KEY-----
```

### Pipeline Triggers

The CI/CD pipeline automatically triggers on:
- **Push to main branch**
- **Push to production branch** 
- **Merged Pull Request** to main/production

### Pipeline Steps
1. **Checkout code**
2. **Build Docker image**
3. **Push to DockerHub**
4. **SSH to EC2 instance**
5. **Pull latest image**
6. **Stop old container**
7. **Start new container**
8. **Clean up old images**

## 💻 Local Development

### Environment Setup
```bash
# Create virtual environment and install dependencies
make install

# Create .env file from template
make env-template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### Development Commands
```bash
# Run application with hot reload
make run

# Run tests
make test

# Code formatting and linting
make format
make lint

# Database operations
make db-create

# Docker operations
make docker-build
make docker-run
make docker-stop
make docker-logs
```

### API Endpoints
- **Health Check**: `GET /health`
- **API Documentation**: `GET /docs`
- **Root**: `GET /`
- **Authentication**: `POST /api/v1/auth/login`
- **Projects**: `GET /api/v1/project/`
- **Student Analysis**: `POST /api/v1/student/analyze`

## 🚀 Deployment

### Automatic Deployment
```bash
# Simply push your code - everything is automated!
git add .
git commit -m "Your changes"
git push origin main

# Monitor deployment in GitHub Actions tab
```

### Manual Deployment
```bash
# Build and push manually
make docker-build
make docker-push

# Or deploy to staging
make deploy-staging
```

### Rolling Back
```bash
# SSH to EC2 instance
ssh -i ~/.ssh/ai-error-solver-key.pem ubuntu@YOUR_EC2_IP

# Pull previous version
docker pull bayajid23/ai-error-solver-backend:previous-tag

# Restart with previous version
docker stop ai-error-solver
docker rm ai-error-solver
docker run -d --name ai-error-solver --restart unless-stopped -p 8000:8000 bayajid23/ai-error-solver-backend:previous-tag
```

## 📊 Monitoring & Troubleshooting

### Health Checks
```bash
# Check application health
curl http://YOUR_EC2_IP:8000/health

# Check from local
make health
```

### Logs and Debugging
```bash
# View application logs
make logs

# SSH to EC2 and check Docker logs
ssh -i ~/.ssh/ai-error-solver-key.pem ubuntu@YOUR_EC2_IP
docker logs -f ai-error-solver

# Check container status
docker ps
docker stats ai-error-solver
```

### Common Issues

#### 1. GitHub Actions Failing
```bash
# Check secrets are properly set
# Verify EC2 is running: aws ec2 describe-instances
# Check SSH key format in secrets
```

#### 2. Docker Build Issues
```bash
# Clean Docker cache
make clean

# Rebuild from scratch
docker build --no-cache -t bayajid23/ai-error-solver-backend:latest .
```

#### 3. EC2 Connection Issues
```bash
# Check security group allows port 8000
aws ec2 describe-security-groups --group-ids YOUR_SG_ID

# Verify EC2 is running
aws ec2 describe-instances --instance-ids YOUR_INSTANCE_ID
```

#### 4. Application Not Starting
```bash
# SSH to EC2 and check logs
ssh -i ~/.ssh/ai-error-solver-key.pem ubuntu@YOUR_EC2_IP
docker logs ai-error-solver

# Check environment variables
docker inspect ai-error-solver
```

## 📚 Commands Reference

### Infrastructure Commands
```bash
make infra-setup          # Setup Pulumi dependencies
make infra-up             # Deploy infrastructure
make infra-down           # Destroy infrastructure
make infra-preview        # Preview changes
make infra-config         # Configure Pulumi stack
```

### Docker Commands
```bash
make docker-build         # Build Docker image
make docker-run           # Run container locally
make docker-stop          # Stop local container
make docker-push          # Push to registry
make docker-pull          # Pull from registry
make docker-logs          # View container logs
```

### Development Commands
```bash
make install              # Install dependencies
make run                  # Run with hot reload
make test                 # Run tests
make lint                 # Check code quality
make format               # Format code
make clean                # Clean Docker cache
```

### Database Commands
```bash
make db-create            # Create database
make db-migrate           # Run migrations
```

### Deployment Commands
```bash
make deploy-local         # Deploy locally
make deploy-staging       # Deploy to staging
make deploy-prod          # Deploy to production
```

### Utility Commands
```bash
make help                 # Show all commands
make health               # Check app health
make logs                 # View application logs
make setup-all            # Complete environment setup
make github-secrets       # Show required GitHub secrets
make create-dockerhub-repo # DockerHub setup instructions
```

## 🏛️ Architecture

### Application Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub Repo   │────│  GitHub Actions  │────│   DockerHub     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                                ▼                        │
┌─────────────────┐    ┌──────────────────┐              │
│   AWS EC2       │◄───│   SSH Deploy     │              │
│                 │    └──────────────────┘              │
│  ┌──────────────┤                                     │
│  │    Docker    │◄────────────────────────────────────┘
│  │  Container   │
│  │              │
│  │  FastAPI App │
│  │  Port 8000   │
│  └──────────────┤
└─────────────────┘
```

### Infrastructure Components
- **VPC**: Custom VPC with public subnet
- **Security Group**: Allows SSH (22), HTTP (80), HTTPS (443), App (8000)
- **EC2 Instance**: t3.micro with Ubuntu 22.04
- **Elastic IP**: Static IP for consistent access
- **Route Table**: Internet gateway routing

### CI/CD Flow
1. **Code Push** → GitHub webhook triggers
2. **GitHub Actions** → Builds Docker image
3. **DockerHub** → Stores container images
4. **EC2 Deployment** → Pulls and runs latest image
5. **Health Check** → Verifies deployment success

## 🔐 Security Considerations

### Environment Variables
- Never commit `.env` files
- Use GitHub Secrets for sensitive data
- Rotate API keys regularly

### SSH Access
- Use key-based authentication only
- Restrict SSH access to your IP if possible
- Keep private keys secure

### Docker Security
- Run containers as non-root user
- Keep base images updated
- Scan images for vulnerabilities

## 📞 Support

### Documentation
- **API Docs**: `http://YOUR_EC2_IP:8000/docs`
- **Redoc**: `http://YOUR_EC2_IP:8000/redoc`

### Troubleshooting
1. Check GitHub Actions logs
2. Verify all secrets are set
3. SSH to EC2 and check Docker logs
4. Ensure all services are running

### Useful Links
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pulumi AWS Guide](https://www.pulumi.com/docs/clouds/aws/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)

---

## 🎉 Quick Test

After complete setup, test your pipeline:

```bash
# Make a small change
echo "# Test change" >> README.md

# Commit and push
git add .
git commit -m "test: trigger CI/CD pipeline"
git push origin main

# Watch the magic happen in GitHub Actions! 🚀
```

Your application will be live at: `http://YOUR_EC2_IP:8000`
