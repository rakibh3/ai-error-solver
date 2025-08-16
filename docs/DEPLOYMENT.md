# Deployment Guide - AI Error Solver Backend

## 🎯 Deployment Overview

This guide covers different deployment scenarios for the AI Error Solver Backend, from local development to production deployment on AWS.

## 🏠 Local Development Deployment

### Quick Local Setup
```bash
# Clone and setup
git clone https://github.com/rakibh3/ai-error-solver-backend.git
cd ai-error-solver-backend
make setup-dev

# Configure environment
cp .env.example .env
nano .env  # Add your API keys

# Run locally
make run
```

### Docker Local Deployment
```bash
# Build and run with Docker
make docker-build
make deploy-local

# Access application
curl http://localhost:8000/health
```

### Local Database Setup
```bash
# Install PostgreSQL locally
sudo apt-get install postgresql postgresql-contrib  # Ubuntu
brew install postgresql                              # macOS

# Create database
sudo -u postgres createdb ai_error_solver

# Update .env with local database URL
DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_error_solver

# Create tables
make db-create
```

## ☁️ AWS Production Deployment

### Infrastructure Deployment

#### Step 1: AWS Prerequisites
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (ap-southeast-1), Output format (json)
```

#### Step 2: Create EC2 Key Pair
```bash
# Create key pair for EC2 access
aws ec2 create-key-pair \
  --key-name ai-error-solver-key \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/ai-error-solver-key.pem

# Set correct permissions
chmod 600 ~/.ssh/ai-error-solver-key.pem
```

#### Step 3: Deploy Infrastructure with Pulumi
```bash
# Setup Pulumi
make setup-infra
cd infra

# Login to Pulumi (free account)
pulumi login

# Create new stack
pulumi stack init production

# Configure stack
pulumi config set aws:region ap-southeast-1
pulumi config set instanceType t3.micro
pulumi config set keyName ai-error-solver-key

# Deploy infrastructure
pulumi up --yes

# Note the outputs:
# - publicIp: Your EC2 public IP address
# - appUrl: Direct URL to your application
# - sshCommand: SSH command to access EC2
```

### Application Deployment

#### Step 4: DockerHub Setup
```bash
# Create DockerHub repository
# 1. Go to https://hub.docker.com
# 2. Sign in or create account
# 3. Click "Create Repository"
# 4. Repository name: ai-error-solver-backend
# 5. Description: AI Error Solver Backend API
# 6. Visibility: Public
# 7. Click "Create"

# Generate access token
# 1. Go to Account Settings > Security
# 2. Click "New Access Token"
# 3. Description: GitHub Actions CI/CD
# 4. Access permissions: Read, Write, Delete
# 5. Generate and copy token
```

#### Step 5: GitHub Secrets Configuration
Add these secrets in GitHub repository (`Settings > Secrets and variables > Actions`):

```bash
# Docker secrets
DOCKERHUB_USERNAME: bayajid23
DOCKERHUB_TOKEN: dckr_pat_your_token_here

# AWS secrets
AWS_ACCESS_KEY_ID: AKIA...
AWS_SECRET_ACCESS_KEY: your_secret_key

# Application secrets
DATABASE_URL: postgresql://user:pass@host:5432/db
GEMINI_API_KEY: AIza...
VOYAGE_API_KEY: pa-...
JWT_SECRET_KEY: your-super-secret-jwt-key
QDRANT_HOST: your-qdrant-host.com
QDRANT_PORT: 6333
QDRANT_API_KEY: your-qdrant-api-key

# EC2 secrets (from Pulumi output)
EC2_PUBLIC_IP: 13.213.xxx.xxx
EC2_SSH_KEY: |
  -----BEGIN RSA PRIVATE KEY-----
  MIIEpAIBAAKCAQEA...
  -----END RSA PRIVATE KEY-----
```

#### Step 6: Automated Deployment
```bash
# Simply push to main branch
git add .
git commit -m "deploy: initial production deployment"
git push origin main

# GitHub Actions will automatically:
# 1. Build Docker image
# 2. Push to DockerHub
# 3. Deploy to EC2
# 4. Start the application
```

## 🔄 CI/CD Pipeline Configuration

### GitHub Actions Workflow
The CI/CD pipeline is configured in `.github/workflows/ci-cd.yml`:

```yaml
# Triggers on:
# - Push to main/production branches
# - Merged pull requests

# Pipeline steps:
# 1. Checkout code
# 2. Build Docker image
# 3. Push to DockerHub
# 4. Deploy to EC2 via SSH
# 5. Health check
```

### Deployment Process
```bash
# Automatic deployment on push
git push origin main

# Manual deployment
make docker-build
make docker-push

# Deploy specific version
docker pull bayajid23/ai-error-solver-backend:specific-tag
# SSH to EC2 and restart with specific tag
```

## 🌐 Production Environment Setup

### Database Configuration

#### Option 1: AWS RDS (Recommended)
```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier ai-error-solver-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password YourSecurePassword123 \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-your-security-group \
  --db-subnet-group-name your-subnet-group

# Update DATABASE_URL in GitHub secrets
DATABASE_URL=postgresql://postgres:YourSecurePassword123@your-rds-endpoint:5432/postgres
```

#### Option 2: Docker PostgreSQL on EC2
```bash
# SSH to EC2
ssh -i ~/.ssh/ai-error-solver-key.pem ubuntu@YOUR_EC2_IP

# Run PostgreSQL container
docker run -d \
  --name postgres-db \
  --restart unless-stopped \
  -e POSTGRES_DB=ai_error_solver \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=YourSecurePassword123 \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15

# Update DATABASE_URL
DATABASE_URL=postgresql://postgres:YourSecurePassword123@localhost:5432/ai_error_solver
```

### Qdrant Vector Database Setup

#### Option 1: Qdrant Cloud (Recommended)
```bash
# 1. Go to https://cloud.qdrant.io
# 2. Create free account
# 3. Create cluster
# 4. Get connection details

# Update secrets
QDRANT_HOST=your-cluster-url.qdrant.io
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key
```

#### Option 2: Self-hosted Qdrant
```bash
# SSH to EC2
ssh -i ~/.ssh/ai-error-solver-key.pem ubuntu@YOUR_EC2_IP

# Run Qdrant container
docker run -d \
  --name qdrant \
  --restart unless-stopped \
  -p 6333:6333 \
  -v qdrant_data:/qdrant/storage \
  qdrant/qdrant

# Update configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=  # Leave empty for local instance
```

## 🔧 Environment-Specific Configurations

### Development Environment
```bash
# .env.development
DEBUG=true
DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_error_solver_dev
QDRANT_HOST=localhost
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
```

### Staging Environment
```bash
# .env.staging
DEBUG=false
DATABASE_URL=postgresql://user:pass@staging-db:5432/ai_error_solver_staging
QDRANT_HOST=staging-qdrant.com
CORS_ORIGINS=["https://staging.yourdomain.com"]
```

### Production Environment
```bash
# .env.production
DEBUG=false
DATABASE_URL=postgresql://user:pass@prod-db:5432/ai_error_solver
QDRANT_HOST=prod-qdrant.com
CORS_ORIGINS=["https://yourdomain.com"]
```

## 📊 Monitoring and Health Checks

### Application Health Check
```bash
# Built-in health endpoint
curl http://YOUR_EC2_IP:8000/health

# Detailed health check
curl http://YOUR_EC2_IP:8000/health/detailed
```

### Infrastructure Monitoring
```bash
# EC2 instance status
aws ec2 describe-instance-status --instance-ids YOUR_INSTANCE_ID

# Application logs
ssh -i ~/.ssh/ai-error-solver-key.pem ubuntu@YOUR_EC2_IP
docker logs -f ai-error-solver

# System resources
docker stats ai-error-solver
```

### Log Management
```bash
# Setup log rotation on EC2
sudo tee /etc/logrotate.d/docker-containers << EOF
/var/lib/docker/containers/*/*.log {
  daily
  missingok
  rotate 7
  compress
  delaycompress
  copytruncate
}
EOF
```

## 🔐 Security Best Practices

### SSL/TLS Setup (Optional)
```bash
# Install Nginx on EC2
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx

# Configure Nginx reverse proxy
sudo tee /etc/nginx/sites-available/ai-error-solver << EOF
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/ai-error-solver /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### Security Group Configuration
```bash
# Update security group to restrict access
aws ec2 authorize-security-group-ingress \
  --group-id YOUR_SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr YOUR_IP/32  # Restrict SSH to your IP only
```

## 🚀 Scaling and Performance

### Horizontal Scaling
```bash
# Use Application Load Balancer with multiple EC2 instances
# Configure auto-scaling group
# Use container orchestration (ECS/EKS)
```

### Vertical Scaling
```bash
# Update instance type in Pulumi config
cd infra
pulumi config set instanceType t3.small  # or t3.medium
pulumi up
```

### Database Optimization
```bash
# RDS performance insights
# Connection pooling
# Read replicas for read-heavy workloads
```

## 🔄 Backup and Recovery

### Database Backup
```bash
# Automated RDS backups
aws rds modify-db-instance \
  --db-instance-identifier ai-error-solver-db \
  --backup-retention-period 7 \
  --apply-immediately

# Manual backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Application Data Backup
```bash
# Backup Qdrant data
docker exec qdrant /bin/bash -c "tar czf /tmp/qdrant_backup.tar.gz /qdrant/storage"
docker cp qdrant:/tmp/qdrant_backup.tar.gz ./qdrant_backup_$(date +%Y%m%d).tar.gz
```

## 🔧 Troubleshooting Deployment Issues

### Common Issues and Solutions

#### 1. GitHub Actions Failing
```bash
# Check secrets configuration
# Verify EC2 instance is running
aws ec2 describe-instances --instance-ids YOUR_INSTANCE_ID

# Check security group allows SSH
aws ec2 describe-security-groups --group-ids YOUR_SG_ID
```

#### 2. Docker Image Build Fails
```bash
# Clean Docker cache
docker system prune -a -f

# Build without cache
docker build --no-cache -t bayajid23/ai-error-solver-backend:latest .
```

#### 3. Application Won't Start
```bash
# SSH to EC2 and check logs
ssh -i ~/.ssh/ai-error-solver-key.pem ubuntu@YOUR_EC2_IP
docker logs ai-error-solver

# Check environment variables
docker inspect ai-error-solver | grep -A 20 '"Env"'

# Test database connection
docker exec ai-error-solver python -c "
from app.core.database import engine
try:
    engine.connect()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

#### 4. High Memory Usage
```bash
# Check container resources
docker stats

# Update container with memory limits
docker run -d \
  --name ai-error-solver \
  --memory=512m \
  --restart unless-stopped \
  -p 8000:8000 \
  bayajid23/ai-error-solver-backend:latest
```

## 📞 Support and Maintenance

### Regular Maintenance Tasks
```bash
# Weekly: Update system packages
sudo apt update && sudo apt upgrade -y

# Monthly: Clean Docker images
docker system prune -f

# Monitor disk usage
df -h
docker system df
```

### Performance Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Monitor application performance
htop
docker stats ai-error-solver
```

### Automated Health Checks
```bash
# Create health check script
tee ~/health_check.sh << 'EOF'
#!/bin/bash
HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): Application is healthy"
else
    echo "$(date): Application is unhealthy (HTTP $RESPONSE)"
    # Restart container if unhealthy
    docker restart ai-error-solver
fi
EOF

chmod +x ~/health_check.sh

# Add to cron for regular checks
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/health_check.sh >> ~/health_check.log 2>&1") | crontab -
```

---

## 🎉 Deployment Checklist

### Pre-deployment
- [ ] AWS CLI configured
- [ ] EC2 key pair created
- [ ] DockerHub repository created
- [ ] All GitHub secrets configured
- [ ] Environment variables set
- [ ] Database setup completed

### Post-deployment
- [ ] Application accessible via EC2 IP
- [ ] Health check endpoint responding
- [ ] API documentation accessible
- [ ] Database connections working
- [ ] Logs are being generated
- [ ] SSL certificate installed (if applicable)
- [ ] Monitoring setup completed
- [ ] Backup strategy implemented

**🚀 Your AI Error Solver Backend is now deployed and ready for production use!**
