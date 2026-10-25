output "cluster_name" {
  description = "Nome do cluster"
  value       = module.cluster.cluster_name
}

output "kubeconfig_command" {
  description = "Comando para configurar o kubectl"
  value       = "aws eks update-kubeconfig --name ${module.cluster.cluster_name} --region ${var.region}"
}
