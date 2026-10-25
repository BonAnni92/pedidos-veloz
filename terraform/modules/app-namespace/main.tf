# Módulo "app-namespace": prepara o namespace da aplicação com governança.
# - Pod Security Admission (rótulos do namespace)
# - ResourceQuota: um HPA mal configurado não consome o cluster inteiro
# - LimitRange: valores padrão para contêineres sem requests/limits

resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.namespace
    labels = {
      "pod-security.kubernetes.io/enforce" = var.pod_security_level
      "pod-security.kubernetes.io/audit"   = var.pod_security_level
      "pod-security.kubernetes.io/warn"    = var.pod_security_level
      "app.kubernetes.io/part-of"          = "pedidos-veloz"
      "app.kubernetes.io/managed-by"       = "terraform"
    }
  }
}

resource "kubernetes_resource_quota_v1" "app" {
  metadata {
    name      = "${var.namespace}-quota"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    hard = {
      "limits.cpu"    = var.quota_cpu_limits
      "limits.memory" = var.quota_memory_limits
      "pods"          = var.quota_pods
    }
  }
}

resource "kubernetes_limit_range_v1" "defaults" {
  metadata {
    name      = "${var.namespace}-defaults"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "500m"
        memory = "256Mi"
      }
      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }
    }
  }
}
