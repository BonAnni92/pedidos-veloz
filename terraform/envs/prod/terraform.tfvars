# Produção: alta disponibilidade em 3 AZs e folga para o pico da campanha
environment         = "prod"
azs                 = ["sa-east-1a", "sa-east-1b", "sa-east-1c"]
node_instance_types = ["m6i.large"]
node_min_size       = 3
node_max_size       = 10
node_desired_size   = 3
single_nat_gateway  = false
