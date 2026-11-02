# Multi-tenancy and scale-out changes

## Tenant identity and authorization

Protected JWT validators require both `sub` and `tenant_id`; tenant IDs are no longer inferred from user IDs. Keep deriving the tenant from signed claims, never from request bodies or query parameters. The `svc-auth` tenant access guard remains synchronous and publishes allowed/denied decision metadata to the durable `kealex.access.audit` RabbitMQ queue. A broker failure must not grant access or break authorization. The event queue is an audit/observation channel, not an authorization decision engine.

## MySQL, RLS, and indexes

The configured backend is MySQL/PyMySQL. MySQL does not provide PostgreSQL-style row-level security policies, so tenant enforcement remains in application queries and schema constraints. The migration `migrations/tenant_scope_indexes_mysql.sql` adds tenant-first composite indexes for common list/filter operations; inspect existing indexes and run once during a low-traffic window. Do not partition tables solely by tenant yet: MySQL partitioning imposes primary/unique-key constraints and should follow measured table growth and query plans. For defense in depth, use composite foreign keys/unique keys that include `tenant_id` when designing future schema changes.

## Connection budget

SQLAlchemy pools default to 3 persistent connections plus 2 overflow connections per process and wait up to 10 seconds. Set `KEALEX_DB_POOL_SIZE`, `KEALEX_DB_MAX_OVERFLOW`, and `KEALEX_DB_POOL_TIMEOUT` consistently across services. Budget worst-case connections as `(pool_size + max_overflow) × service replicas × worker processes`, then reserve headroom for migrations, administration, and other consumers. `svc-auth` exposes Prometheus metrics at `/metrics` for access decisions and checked-out DB connections.

## Shared file storage

`svc-arquivos` uses the Docker named volume `kealex-uploads`, which is shared between replicas on the same Docker host. A local named volume is not shared across Docker hosts. Multi-host deployments must mount a shared filesystem volume (such as NFS) or adopt an object-storage adapter before scaling across nodes. The existing `svc-documentos` analysis endpoint still stores extracted text in MySQL and has not been switched to this service.
