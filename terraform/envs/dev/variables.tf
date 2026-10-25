variable "region" {
  description = "Região AWS"
  type        = string
  default     = "sa-east-1"
}

variable "environment" {
  description = "Nome do ambiente"
  type        = string
}

variable "azs" {
  description = "Zonas de disponibilidade"
  type        = list(string)
}

variable "node_instance_types" {
  description = "Tipos de instância dos nós"
  type        = list(string)
}

variable "node_min_size" {
  description = "Mínimo de nós"
  type        = number
}

variable "node_max_size" {
  description = "Máximo de nós"
  type        = number
}

variable "node_desired_size" {
  description = "Nós iniciais"
  type        = number
}

variable "single_nat_gateway" {
  description = "Usar um único NAT Gateway"
  type        = bool
}
