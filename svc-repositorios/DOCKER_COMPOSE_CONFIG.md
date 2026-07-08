# Adicione esta seção ao seu docker-compose.yml

svc-repositorios:
  build: ./svc-repositorios
  container_name: svc-repositorios
  environment:
    DATABASE_URL: ${DATABASE_URL}
    SECRET_KEY: ${SECRET_KEY}
    STORAGE_PATH: /app/storage
    GDRIVE_TOKEN: ${GDRIVE_TOKEN:-}
  volumes:
    - ./storage:/app/storage
    - /var/documentos:/var/documentos:ro
  ports:
    - "8007:8000"
  depends_on:
    - mysql
  networks:
    - kealex-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.svc-repositorios.rule=PathPrefix(`/k1/lex/repositorios`)"
    - "traefik.http.services.svc-repositorios.loadbalancer.server.port=8000"
