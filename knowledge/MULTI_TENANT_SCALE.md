# Multi-tenancy and scale-out changes

## Tenant identity and authorization

Protected JWT validators require both `sub` and `tenant_id`; tenant IDs are no longer inferred from user IDs. Keep deriving the tenant from signed claims, never from request bodies or query parameters. The `svc-auth` tenant access guard remains synchronous and publishes allowed/denied decision metadata to the durable `kealex.access.audit` RabbitMQ queue. A broker failure must not grant access or break authorization. The event queue is an audit/observation channel, not an authorization decision engine.

## MySQL, RLS, and indexes

The configured backend is MySQL/PyMySQL. MySQL does not provide PostgreSQL-style row-level security policies, so tenant enforcement remains in application queries and schema constraints. The migration `migrations/tenant_scope_indexes_mysql.sql` adds tenant-first composite indexes for common list/filter operations; inspect existing indexes and run once during a low-traffic window. Do not partition tables solely by tenant yet: MySQL partitioning imposes primary/unique-key constraints and should follow measured table growth and query plans. For defense in depth, use composite foreign keys/unique keys that include `tenant_id` when designing future schema changes.

## Connection budget

SQLAlchemy pools default to 2 persistent connections plus 1 overflow connection per process and wait up to 10 seconds. Set `KEALEX_DB_POOL_SIZE`, `KEALEX_DB_MAX_OVERFLOW`, and `KEALEX_DB_POOL_TIMEOUT` consistently across services. Budget worst-case connections as `(pool_size + max_overflow) × service replicas × worker processes`; for the eight database-backed services in the primary Compose file, one process each can use up to 24 connections. Reserve headroom for migrations, administration, and other consumers, and lower or raise these defaults only after checking the MySQL connection limit and observed pool metrics. `svc-auth` exposes Prometheus metrics at `/metrics` for access decisions and checked-out DB connections.

## Authorization across services

The signed JWT establishes user and tenant identity. Each business API then checks the current tenant entitlement in MySQL and fails closed for missing, inactive, expired, or unpaid tenants. `svc-auth` keeps identity-only validation on login and subscription-recovery routes so an expired tenant can still restore service. These request-time checks are synchronous by design; RabbitMQ carries audit events to a separate worker and is not the source of truth for granting access.

## Scale-out routing

The primary `docker-compose.yml` routes `hubkealex` and `svc-cobrancas` through Traefik and does not publish per-container host ports or fixed container names. This permits multiple replicas on the same Docker host. Docker Compose's local named volumes and a single RabbitMQ broker remain single-host components; multi-host availability requires shared file storage and a broker deployment designed for multiple nodes.

Example for the primary Compose file: `docker compose up -d --scale hubkealex=3 --scale svc-cobrancas=3`. Scale the independent audit worker separately with `docker compose up -d --scale kealex-svc-auth-worker=2`. Do not scale RabbitMQ by increasing the replica count of the current single-node service; broker clustering needs a deliberate multi-node deployment.

## Shared file storage

`svc-arquivos` uses the Docker named volume `kealex-uploads`, which is shared between replicas on the same Docker host. A local named volume is not shared across Docker hosts. Multi-host deployments must mount a shared filesystem volume (such as NFS) or adopt an object-storage adapter before scaling across nodes. The existing `svc-documentos` analysis endpoint still stores extracted text in MySQL and has not been switched to this service.
