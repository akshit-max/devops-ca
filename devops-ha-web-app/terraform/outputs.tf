output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}


output "instance_1_public_ip" {
  description = "Public IP of EC2 server 1"
  value       = aws_instance.app[0].public_ip
}


output "instance_2_public_ip" {
  description = "Public IP of EC2 server 2"
  value       = aws_instance.app[1].public_ip
}


output "instance_1_private_ip" {
  description = "Private IP of EC2 server 1"
  value       = aws_instance.app[0].private_ip
}


output "instance_2_private_ip" {
  description = "Private IP of EC2 server 2"
  value       = aws_instance.app[1].private_ip
}


output "load_balancer_dns" {
  description = "Application Load Balancer DNS"
  value       = aws_lb.main.dns_name
}

output "github_actions_role_arn" {
  description = "IAM Role ARN for GitHub Actions OIDC"
  value       = aws_iam_role.github_actions.arn
}

output "instance_1_id" {
  description = "ID of EC2 server 1"
  value       = aws_instance.app[0].id
}

output "instance_2_id" {
  description = "ID of EC2 server 2"
  value       = aws_instance.app[1].id
}
