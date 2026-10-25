-- Executado apenas na primeira inicialização do volume do PostgreSQL.
-- Um banco por serviço ("database per service"): Pedidos e Estoque não
-- compartilham tabelas, apenas a mesma instância (simplificação do MVP).
CREATE DATABASE pedidos;
CREATE DATABASE estoque;
