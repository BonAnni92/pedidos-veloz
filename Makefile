# Atalhos do projeto (opcional: todos os comandos também estão no README)
SERVICES := gateway pedidos estoque pagamentos

.PHONY: up down logs ps smoke load test lint k8s-kind k8s-deploy k8s-clean

up:            ## Sobe todo o ambiente local (um único comando)
	docker compose up -d --build

down:          ## Derruba o ambiente e apaga os volumes
	docker compose down -v

logs:          ## Acompanha os logs (JSON) dos microsserviços
	docker compose logs -f gateway pedidos estoque pagamentos

ps:
	docker compose ps

smoke:         ## Teste ponta a ponta pelo API Gateway
	bash scripts/smoke-test.sh http://localhost:8080

load:          ## Gera carga por 2 minutos (alimenta Grafana / HPA)
	python3 scripts/load_test.py --url http://localhost:8080 --duracao 120 --concorrencia 20

test:          ## Testes de todos os serviços
	@for s in $(SERVICES); do echo "== $$s"; pytest services/$$s || exit 1; done

lint:
	ruff check .

k8s-kind:      ## Cria cluster kind (Codespaces). No Rancher Desktop não é preciso.
	bash scripts/kind-up.sh

k8s-deploy:    ## Build + deploy no Kubernetes local
	bash scripts/k8s-deploy.sh

k8s-clean:
	kubectl delete namespace loja-veloz observability --ignore-not-found
