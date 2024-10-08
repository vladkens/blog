terraform {
  required_providers {
    aws   = { source = "hashicorp/aws", version = "~> 5" }
    local = { source = "hashicorp/local", version = "~> 2" }
  }
}

provider "aws" {
  profile = "default"   # Change this to your AWS profile
  region  = "us-east-1" # Change this to your AWS region
}

# MARK: Getting VPC and Subnets

locals {
  vpc_name = "my-vpc" # Change this to yor VPC name
}

data "aws_vpc" "vpc" {
  filter {
    name   = "tag:Name"
    values = [local.vpc_name]
  }
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.vpc.id]
  }

  tags = { Tier = "Public" } # This is custom tag
}

# MARK: Config

locals {
  wg_cidr = "172.16.16.0/20" # CIDR of Wireguard Server
  wg_port = 51820            # Port of Wireguard Server
  secrets = yamldecode(file("secrets.yaml"))

  userdata = templatefile("templates/wg-init.tpl", {
    wg_cidr    = local.wg_cidr
    wg_port    = local.wg_port
    wg_privkey = local.secrets.wg_server.privkey
    wg_peers = join("\n", [
      for p in local.secrets.wg_peers :
      templatefile("templates/wg-peer.tpl", {
        peer_name   = p.name
        peer_pubkey = p.pubkey
        peer_addr   = p.addr
      })
    ])
  })
}

# MARK: Server dependencies

data "aws_ami" "ubuntu" {
  owners      = ["099720109477"] # Canonical
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
  }
}

resource "aws_eip" "wireguard" {
  tags = { Name = "wireguard" }
}

resource "aws_security_group" "wireguard" {
  name        = "${local.vpc_name}-wireguard"
  description = "SG for Wireguard VPN Server"
  vpc_id      = data.aws_vpc.vpc.id
  ingress {
    from_port   = local.wg_port
    to_port     = local.wg_port
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow Wireguard Traffic"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# MARK: Server

resource "aws_instance" "wireguard" {
  count                       = 1
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t4g.nano"
  subnet_id                   = data.aws_subnets.public.ids[0]
  vpc_security_group_ids      = [aws_security_group.wireguard.id]
  user_data                   = local.userdata
  user_data_replace_on_change = true
  tags                        = { Name = "wireguard" }
}

resource "aws_eip_association" "wireguard" {
  instance_id   = aws_instance.wireguard[0].id
  allocation_id = aws_eip.wireguard.id
}

# MARK: Export client configuration

locals {
  # https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html#AmazonDNS
  client_dns = ["169.254.169.253", "1.1.1.1", "1.0.0.1"]
  client_routes = [
    data.aws_vpc.vpc.cidr_block, # All IPs in the VPC
    "169.254.169.253/32",        # AWS DNS
    # "0.0.0.0/32",                # Route all traffic through VPN (uncomment if you want this)
  ]
}

resource "local_file" "peer_conf" {
  for_each = { for index, p in local.secrets.wg_peers : p.name => p }
  filename = "generated/${each.value.name}.conf"
  content = templatefile("templates/client-conf.tpl", {
    server_addr    = "${aws_eip.wireguard.public_ip}:${local.wg_port}",
    server_pubkey  = local.secrets.wg_server.pubkey,
    client_addr    = each.value.addr,
    client_privkey = each.value.privkey,
    client_dns     = join(",", local.client_dns),
    client_routes  = join(",", local.client_routes),
  })
}
