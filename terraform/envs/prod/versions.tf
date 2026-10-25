terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.95"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.36"
    }
  }

  # State remoto e compartilhado (S3 + lock nativo), configurado na inicialização:
  #   terraform init -backend-config=backend.hcl
  # Assim o time inteiro (e o pipeline) enxerga o MESMO estado da infraestrutura.
  backend "s3" {}
}
