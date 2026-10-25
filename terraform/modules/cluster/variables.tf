variable "name" {
  description = "Prefixo dos recursos (ex.: pedidos-veloz-dev)"
  type        = string
}

variable "kubernetes_version" {
  description = "Versão do Kubernetes do EKS"
  type        = string
  default     = "1.31"
}

variable "vpc_cidr" {
  description = "Bloco CIDR da VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "azs" {
  description = "Zonas de disponibilidade (mínimo 2 para alta disponibilidade)"
  type        = list(string)
}

variable "node_instance_types" {
  description = "Tipos de instância dos nós"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_min_size" {
  description = "Mínimo de nós do grupo gerenciado"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Máximo de nós (o Cluster Autoscaler/Karpenter escala até aqui)"
  type        = number
  default     = 4
}

variable "node_desired_size" {
  description = "Quantidade inicial de nós"
  type        = number
  default     = 2
}

variable "single_nat_gateway" {
  description = "true = 1 NAT (mais barato, dev); false = 1 NAT por AZ (HA, prod)"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags aplicadas a todos os recursos (custo, dono, ambiente)"
  type        = map(string)
  default     = {}
}
