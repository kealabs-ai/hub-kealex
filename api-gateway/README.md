# API Gateway - Nginx Configuration

This directory contains the nginx configuration for the Kealex API Gateway.

## Files

- `nginx.conf` - Main nginx configuration (HTTP)
- `nginx-ssl.conf` - Production nginx configuration with SSL
- `Dockerfile` - Docker build file
- `switch-nginx.sh` - Script to switch between configurations

## Configuration Features

### Current nginx.conf includes:

1. **Upstream Definitions** - Separate upstream blocks for each microservice
2. **CORS Headers** - Full CORS support for frontend integration
3. **Security Headers** - X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
4. **Gzip Compression** - For better performance
5. **Timeout Settings** - 30s connect/send/read timeouts
6. **Buffer Settings** - Optimized proxy buffers
7. **Health Check Endpoint** - `/health` endpoint for monitoring
8. **Backward Compatibility** - Redirects from old URLs to `/v1/lex/` prefix
9. **Error Pages** - Custom error pages

### Endpoints Routing

All endpoints are prefixed with `/v1/lex/`:

- `/v1/lex/auth` → svc-auth:8000
- `/v1/lex/processos` → svc-processos:8000  
- `/v1/lex/documentos` → svc-documentos:8000
- `/v1/lex/financeiro` → svc-financeiro:8000
- `/v1/lex/prazos` → svc-prazos:8000
- `/v1/lex/usuarios` → svc-usuarios:8000
- `/v1/lex/configuracoes` → svc-configuracoes:8000
- `/v1/lex/escritorios` → svc-escritorios:8000
- `/v1/lex/clientes` → svc-clientes:8000

## Testing

### Test nginx configuration:

```bash
# Test configuration syntax
docker exec kealex-api-gateway nginx -t

# Test health endpoint
curl http://localhost:8000/health

# Test CORS headers
curl -I -X OPTIONS http://localhost:8000/v1/lex/auth

# Test backward compatibility redirect
curl -I http://localhost:8000/auth
```

### Using the switch script:

```bash
# Inside the container
docker exec -it kealex-api-gateway /bin/sh

# Switch to SSL configuration (requires SSL certificates)
switch-nginx ssl

# Switch back to normal configuration
switch-nginx normal

# Test configuration
switch-nginx test

# Check status
switch-nginx status
```

## Production Deployment with SSL

For production deployment with SSL:

1. Place SSL certificates in the container:
   - Certificate: `/etc/ssl/certs/kealex.crt`
   - Private key: `/etc/ssl/private/kealex.key`

2. Update `nginx-ssl.conf` with your domain name:
   ```nginx
   server_name kealex.com www.kealex.com;
   ```

3. Switch to SSL configuration:
   ```bash
   docker exec kealex-api-gateway switch-nginx ssl
   ```

## Troubleshooting

### Check nginx logs:
```bash
docker logs kealex-api-gateway
```

### Check active connections:
```bash
docker exec kealex-api-gateway nginx -T | head -20
```

### Restart nginx:
```bash
docker exec kealex-api-gateway nginx -s reload
```

### Rebuild and restart:
```bash
docker-compose build api-gateway
docker-compose up -d api-gateway
```