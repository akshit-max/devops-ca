# DevOps Highly Available Web Application

## Case Study

Designing a Highly Available Web Architecture with Automated Deployment using Terraform and AWS.

## Technologies

- Python
- Flask
- Docker
- Git
- GitHub
- GitHub Actions
- Terraform
- AWS EC2
- AWS VPC
- AWS Application Load Balancer
- AWS CloudWatch

## Architecture

The application will be deployed on two EC2 instances located in different Availability Zones.

An Application Load Balancer will distribute incoming traffic between the instances.

Terraform will be used to automate AWS infrastructure creation.

GitHub Actions will automate application testing and deployment.

## DevOps Flow

Developer
→ GitHub
→ GitHub Actions
→ Test
→ Docker Build
→ Deploy
→ AWS

## High Availability

Two EC2 instances will run the application.

If one instance becomes unavailable, the Load Balancer can route traffic to the healthy instance.

## Infrastructure as Code

Terraform will manage:

- VPC
- Subnets
- Internet Gateway
- Route Table
- Security Groups
- EC2 Instances
- Application Load Balancer
- Target Group

## Application Endpoints

### Home

/

### Health Check

/health
