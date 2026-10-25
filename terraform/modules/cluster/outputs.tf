output "cluster_name" {
  description = "Nome do cluster EKS"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint da API do Kubernetes"
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "CA do cluster (base64)"
  value       = module.eks.cluster_certificate_authority_data
}

output "vpc_id" {
  description = "ID da VPC"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "Subnets privadas (ex.: para um RDS PostgreSQL gerenciado)"
  value       = module.vpc.private_subnets
}
