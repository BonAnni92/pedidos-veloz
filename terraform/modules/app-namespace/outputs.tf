output "namespace" {
  description = "Namespace criado"
  value       = kubernetes_namespace_v1.app.metadata[0].name
}
