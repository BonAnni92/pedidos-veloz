# Ambiente composto a partir dos módulos reutilizáveis. dev e prod usam
# EXATAMENTE o mesmo código; só mudam os valores em terraform.tfvars.

locals {
  name = "pedidos-veloz-${var.environment}"
  tags = {
    Project     = "pedidos-veloz"
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = "time-plataforma"
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = local.tags
  }
}

module "cluster" {
  source = "../../modules/cluster"

  name                = local.name
  azs                 = var.azs
  node_instance_types = var.node_instance_types
  node_min_size       = var.node_min_size
  node_max_size       = var.node_max_size
  node_desired_size   = var.node_desired_size
  single_nat_gateway  = var.single_nat_gateway
  tags                = local.tags
}

# O provider Kubernetes autentica no cluster recém-criado via AWS CLI.
provider "kubernetes" {
  host                   = module.cluster.cluster_endpoint
  cluster_ca_certificate = base64decode(module.cluster.cluster_certificate_authority_data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.cluster.cluster_name, "--region", var.region]
  }
}

module "app_namespace" {
  source = "../../modules/app-namespace"

  namespace          = "loja-veloz"
  pod_security_level = "restricted"
}
