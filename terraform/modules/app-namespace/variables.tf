variable "namespace" {
  description = "Nome do namespace da aplicação"
  type        = string
  default     = "loja-veloz"
}

variable "pod_security_level" {
  description = "Nível do Pod Security Admission: privileged, baseline ou restricted"
  type        = string
  default     = "restricted"

  validation {
    condition     = contains(["privileged", "baseline", "restricted"], var.pod_security_level)
    error_message = "Use privileged, baseline ou restricted."
  }
}

variable "quota_cpu_limits" {
  description = "Soma máxima de limits de CPU no namespace (protege o cluster)"
  type        = string
  default     = "16"
}

variable "quota_memory_limits" {
  description = "Soma máxima de limits de memória no namespace"
  type        = string
  default     = "16Gi"
}

variable "quota_pods" {
  description = "Número máximo de Pods (comporta o máximo dos HPAs)"
  type        = string
  default     = "60"
}
