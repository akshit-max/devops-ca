data "aws_ami" "ubuntu" {
  most_recent = true

  owners = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}



locals {
  user_data = <<-EOF
              #!/bin/bash

              apt-get update -y

              apt-get install -y ca-certificates curl

              install -m 0755 -d /etc/apt/keyrings

              curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
                -o /etc/apt/keyrings/docker.asc

              chmod a+r /etc/apt/keyrings/docker.asc

              echo \
              "Types: deb
              URIs: https://download.docker.com/linux/ubuntu
              Suites: $(. /etc/os-release && echo "$${UBUNTU_CODENAME:-$VERSION_CODENAME}")
              Components: stable
              Architectures: $(dpkg --print-architecture)
              Signed-By: /etc/apt/keyrings/docker.asc" \
              > /etc/apt/sources.list.d/docker.sources

              apt-get update -y

              apt-get install -y \
                docker-ce \
                docker-ce-cli \
                containerd.io \
                docker-buildx-plugin \
                docker-compose-plugin

              systemctl enable docker
              systemctl start docker

              snap install amazon-ssm-agent --classic
              snap start amazon-ssm-agent
              systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
              systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service
              EOF
}


resource "aws_instance" "app" {
  count = 2

  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type

  subnet_id = count.index == 0 ? aws_subnet.public_a.id : aws_subnet.public_b.id

  vpc_security_group_ids = [
    aws_security_group.ec2.id
  ]

  key_name = "devops-ha-web-app-key"

  iam_instance_profile = aws_iam_instance_profile.ec2.name

  associate_public_ip_address = true

  user_data = local.user_data

  tags = {
    Name = "${var.project_name}-server-${count.index + 1}"
  }

  lifecycle {
    ignore_changes = [user_data]
  }
}
