# Quick Setup Guide - AI Error Solver Backend

## 🚀 5-Minute Setup

### Prerequisites Check
```bash
# Verify you have these installed
docker --version
aws --version
curl -fsSL https://get.pulumi.com | sh
```

### 1. Repository Setup
```bash
git clone https://github.com/rakibh3/ai-error-solver-backend.git
cd ai-error-solver-backend
make setup-dev
```

### 2. Environment Configuration
```bash
# Copy and edit environment file
cp .env.example .env
nano .env  # Add your API keys
```

### 3. AWS & Infrastructure
```bash
# Configure AWS
aws configure

# Create EC2 key pair
aws ec2 create-key-pair --key-name ai-error-solver-key --query 'KeyMaterial' --output text > ~/.ssh/ai-error-solver-key.pem
chmod 600 ~/.ssh/ai-error-solver-key.pem

# Setup and deploy infrastructure
make setup-infra
cd infra
pulumi login
pulumi stack init production
pulumi config set aws:region ap-southeast-1
pulumi config set keyName ai-error-solver-key
make infra-up
```

### 4. DockerHub Repository
```bash
# Create repository at https://hub.docker.com
# Repository name: ai-error-solver-backend
# Visibility: Public
```

### 5. GitHub Secrets
Add these in GitHub Repository Settings → Secrets and variables → Actions:

**Required Secrets:**
```
DOCKERHUB_USERNAME=bayajid23
DOCKERHUB_TOKEN=your_dockerhub_token
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
DATABASE_URL=your_database_url
GEMINI_API_KEY=your_gemini_key
VOYAGE_API_KEY=your_voyage_key
JWT_SECRET_KEY=your_jwt_secret
QDRANT_HOST=your_qdrant_host
QDRANT_PORT=6333
QDRANT_API_KEY=your_qdrant_key
EC2_PUBLIC_IP=your_ec2_ip_from_pulumi_output
EC2_SSH_KEY=your_private_key_content
```

### 6. Deploy
```bash
# Push to trigger automatic deployment
git add .
git commit -m "initial setup"
git push origin main
```

### 7. Verify
```bash
# Check deployment
curl http://YOUR_EC2_IP:8000/health
curl http://YOUR_EC2_IP:8000/docs
```

## 🔄 Daily Workflow

```bash
# Make changes
nano app/main.py

# Push changes (triggers automatic deployment)
git add .
git commit -m "feature: new functionality"
git push origin main

# Monitor deployment in GitHub Actions
# App automatically updates on EC2!
```

## 🛠️ Useful Commands

```bash
make help                 # Show all available commands
make run                  # Run locally for development
make docker-build         # Build Docker image
make infra-preview        # Preview infrastructure changes
make health              # Check app health
make logs                # View application logs
```

## 🚨 Troubleshooting

### GitHub Actions Failing?
- Check all secrets are properly set
- Verify EC2 instance is running
- Check SSH key format in secrets

### Can't Access Application?
```bash
# Check EC2 security group
aws ec2 describe-security-groups --group-ids YOUR_SG_ID

# SSH to EC2 and check Docker
ssh -i ~/.ssh/ai-error-solver-key.pem ubuntu@YOUR_EC2_IP
docker ps
docker logs ai-error-solver
```

### Local Development Issues?
```bash
# Install dependencies
make install

# Check environment
cat .env

# Run locally
make run
```

## 📞 Need Help?

1. **GitHub Issues**: Create an issue in the repository
2. **Logs**: Check GitHub Actions logs for CI/CD issues
3. **Documentation**: Full documentation in `docs/README.md`

---

**🎉 Once setup is complete, just push code and watch it deploy automatically!**
