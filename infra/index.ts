import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";

// Get configuration
const config = new pulumi.Config();
const instanceType = config.get("instanceType") || "t3.micro";
const keyName = config.get("keyName") || "ai-error-solver-key";

// Create VPC
const vpc = new aws.ec2.Vpc("ai-error-solver-vpc", {
    cidrBlock: "10.0.0.0/16",
    enableDnsHostnames: true,
    enableDnsSupport: true,
    tags: {
        Name: "ai-error-solver-vpc",
        Project: "ai-error-solver"
    }
});

// Create Internet Gateway
const igw = new aws.ec2.InternetGateway("ai-error-solver-igw", {
    vpcId: vpc.id,
    tags: {
        Name: "ai-error-solver-igw",
        Project: "ai-error-solver"
    }
});

// Create public subnet
const publicSubnet = new aws.ec2.Subnet("ai-error-solver-public-subnet", {
    vpcId: vpc.id,
    cidrBlock: "10.0.1.0/24",
    availabilityZone: "us-east-1a",
    mapPublicIpOnLaunch: true,
    tags: {
        Name: "ai-error-solver-public-subnet",
        Project: "ai-error-solver"
    }
});

// Create route table
const routeTable = new aws.ec2.RouteTable("ai-error-solver-rt", {
    vpcId: vpc.id,
    routes: [
        {
            cidrBlock: "0.0.0.0/0",
            gatewayId: igw.id,
        }
    ],
    tags: {
        Name: "ai-error-solver-rt",
        Project: "ai-error-solver"
    }
});

// Associate route table with subnet
const rtAssociation = new aws.ec2.RouteTableAssociation("ai-error-solver-rta", {
    subnetId: publicSubnet.id,
    routeTableId: routeTable.id,
});

// Create security group
const securityGroup = new aws.ec2.SecurityGroup("ai-error-solver-sg", {
    vpcId: vpc.id,
    description: "Security group for AI Error Solver backend",
    ingress: [
        {
            fromPort: 22,
            toPort: 22,
            protocol: "tcp",
            cidrBlocks: ["0.0.0.0/0"],
            description: "SSH"
        },
        {
            fromPort: 8000,
            toPort: 8000,
            protocol: "tcp",
            cidrBlocks: ["0.0.0.0/0"],
            description: "FastAPI app"
        },
        {
            fromPort: 80,
            toPort: 80,
            protocol: "tcp",
            cidrBlocks: ["0.0.0.0/0"],
            description: "HTTP"
        },
        {
            fromPort: 443,
            toPort: 443,
            protocol: "tcp",
            cidrBlocks: ["0.0.0.0/0"],
            description: "HTTPS"
        }
    ],
    egress: [
        {
            fromPort: 0,
            toPort: 0,
            protocol: "-1",
            cidrBlocks: ["0.0.0.0/0"],
            description: "All outbound traffic"
        }
    ],
    tags: {
        Name: "ai-error-solver-sg",
        Project: "ai-error-solver"
    }
});

// Get latest Ubuntu AMI
const ubuntu = aws.ec2.getAmi({
    mostRecent: true,
    owners: ["099720109477"], // Canonical
    filters: [
        {
            name: "name",
            values: ["ubuntu/images/hvm-ssd/ubuntu-22.04-amd64-server-*"],
        }
    ],
});

// User data script to install Docker
const userData = `#!/bin/bash
# Update system
apt-get update
apt-get upgrade -y

# Install Docker
apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create deployment script
cat > /home/ubuntu/deploy.sh << 'EOF'
#!/bin/bash
# Pull latest image
docker pull bayajid23/ai-error-solver-backend:latest

# Stop existing container
docker stop ai-error-solver || true
docker rm ai-error-solver || true

# Run new container
docker run -d \\
  --name ai-error-solver \\
  --restart unless-stopped \\
  -p 8000:8000 \\
  bayajid23/ai-error-solver-backend:latest

# Clean up old images
docker image prune -f
EOF

chmod +x /home/ubuntu/deploy.sh
chown ubuntu:ubuntu /home/ubuntu/deploy.sh

# Create log directory
mkdir -p /var/log/ai-error-solver
chown ubuntu:ubuntu /var/log/ai-error-solver
`;

// Create EC2 instance
const instance = new aws.ec2.Instance("ai-error-solver-instance", {
    ami: ubuntu.then(ubuntu => ubuntu.id),
    instanceType: instanceType,
    keyName: keyName,
    subnetId: publicSubnet.id,
    vpcSecurityGroupIds: [securityGroup.id],
    userData: userData,
    tags: {
        Name: "ai-error-solver-backend",
        Project: "ai-error-solver"
    }
});

// Create Elastic IP
const eip = new aws.ec2.Eip("ai-error-solver-eip", {
    instance: instance.id,
    domain: "vpc",
    tags: {
        Name: "ai-error-solver-eip",
        Project: "ai-error-solver"
    }
});

// Outputs
export const vpcId = vpc.id;
export const publicSubnetId = publicSubnet.id;
export const securityGroupId = securityGroup.id;
export const instanceId = instance.id;
export const publicIp = eip.publicIp;
export const privateIp = instance.privateIp;
export const sshCommand = pulumi.interpolate`ssh -i ~/.ssh/${keyName}.pem ubuntu@${eip.publicIp}`;
export const appUrl = pulumi.interpolate`http://${eip.publicIp}:8000`;
export const docsUrl = pulumi.interpolate`http://${eip.publicIp}:8000/docs`;
