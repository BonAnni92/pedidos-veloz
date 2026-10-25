# Desenvolvimento: menor custo
environment         = "dev"
azs                 = ["sa-east-1a", "sa-east-1b"]
node_instance_types = ["t3.medium"]
node_min_size       = 1
node_max_size       = 3
node_desired_size   = 2
single_nat_gateway  = true
