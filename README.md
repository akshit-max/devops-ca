# DevOps Highly Available Web Application (CA-1 Project)

This project demonstrates a complete, professional, highly available web application deployment on AWS using Terraform, Docker, and GitHub Actions CI/CD.

## Architecture

```text
                    INTERNET
                       │
                       ▼
              ┌─────────────────┐
              │       ALB       │
              │ Health Checks   │
              └────────┬────────┘
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
        ┌─────────┐         ┌─────────┐
        │ EC2-1   │         │ EC2-2   │
        │ AZ-A    │         │ AZ-B    │
        │ Docker  │         │ Docker  │
        │ Flask   │         │ Flask   │
        └─────────┘         └─────────┘
             ▲                   ▲
             └─────────┬─────────┘
                       │
                  AWS SSM
                       ▲
                       │
                 GitHub Actions
                       ▲
                       │
                    GitHub
```

The system uses:
- **Flask**: Python web framework serving a professional monitoring dashboard.
- **Docker**: Containerizes the application.
- **Terraform**: Infrastructure as Code for provisioning AWS resources.
- **AWS EC2**: Hosts the Docker containers across two Availability Zones for high availability.
- **AWS ALB**: Application Load Balancer distributes traffic and performs health checks.
- **AWS Systems Manager (SSM)**: Securely deploys the application without exposing SSH.
- **AWS CloudWatch**: Collects and visualizes infrastructure metrics.
- **GitHub Actions**: Automated CI/CD pipeline using OIDC authentication.

## Local Setup & Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run tests:**
   ```bash
   pytest
   ```
3. **Run application locally:**
   ```bash
   python app.py
   ```
   *Note: Real AWS CloudWatch metrics will not load locally unless AWS CLI is configured with correct permissions.*

## Infrastructure Deployment (Terraform)

Deploy the AWS infrastructure before triggering the CI/CD pipeline.

```bash
cd terraform
terraform init
terraform validate
terraform plan
terraform apply
```

To destroy the infrastructure when finished:
```bash
terraform destroy
```

## CI/CD Pipeline & GitHub Actions

The pipeline automatically runs on every push to `main`.
It uses **AWS OIDC** to securely authenticate with AWS. No long-lived access keys are required!

**Pipeline Flow:**
1. Run Pytest
2. Build Docker Image
3. Push to public GHCR
4. Trigger AWS SSM to pull the new image and restart the containers on both EC2 instances.

## Demonstration Guide

### 1. Load Balancing & Dashboard
Access the ALB DNS URL. The dashboard will display real-time AWS metrics, server health, and the currently serving EC2 instance. Refresh the page to see the ALB load balancing traffic between the two instances.

### 2. Fault Tolerance & Failover Simulation
To demonstrate automatic failover:
1. Open the AWS EC2 Console.
2. Select one of the instances (e.g., `devops-ha-web-app-server-1`) and click **Instance state > Stop instance**.
3. Watch the dashboard:
   - The stopped server will turn 🔴 UNHEALTHY.
   - The overall status will change to 🟡 DEGRADED.
   - The Failover Status will show ⚠️ Failover Active.
   - All traffic will automatically route to the remaining healthy server.

### 3. Recovery Demonstration
1. Start the stopped EC2 instance again.
2. Watch the dashboard:
   - The server will boot up and the Docker container will start automatically.
   - The ALB will pass health checks.
   - The server will turn 🟢 HEALTHY again.
   - The overall status will return to 🟢 HEALTHY.

## Security
- **No SSH exposed to the internet**. Port 22 is restricted to a single IP.
- **No hardcoded AWS credentials**. GitHub Actions uses OIDC.
- EC2 instances fetch their own CloudWatch metrics using IAM Instance Profiles.
