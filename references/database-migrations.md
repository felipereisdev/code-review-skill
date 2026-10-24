# Zero-Downtime Database Migrations *(only if the diff includes migrations)*

- **Additive changes first**: new columns added as nullable or with a default before application code uses them
- **No instant NOT NULL without default**: adding a NOT NULL column without a default on a large table causes a full table lock
- **Column/table rename safety**: old column kept alongside new one during a transition period; renamed in a follow-up migration after code is deployed
- **Column removal safety**: column removed only after code no longer references it and the deployment is stable
- **Index creation**: indexes on large tables created concurrently (e.g. `CREATE INDEX CONCURRENTLY`) to avoid locking
- **Reversibility**: `down` method correctly undoes the `up` method without data loss
