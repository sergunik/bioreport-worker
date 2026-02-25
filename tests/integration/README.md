# Integration tests

Require a running PostgreSQL instance and a test database with the schema applied.

## Setup

1. Create the test database:
   ```bash
   createdb bioreport_test
   ```

2. Apply the schema:
   ```bash
   psql -d bioreport_test -f tests/integration/schema.sql
   ```

3. (Optional) Set env for a different test DB:
   - `DB_DATABASE` (default in conftest: `bioreport_test`)
   - `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`

## Run

```bash
pytest tests/integration -m integration -v
```

To run all tests including integration:

```bash
pytest -m integration -v
```
