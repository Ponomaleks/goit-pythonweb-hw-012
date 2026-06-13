# Alembic Migration Guide

This document explains how schema migrations work in this project.

## How Alembic Works

Alembic versions database schema changes. Each revision file describes how to move the schema forward (`upgrade`) or backward (`downgrade`).

### Migration Layout

```text
migrations/
  env.py         # Alembic runtime config, loads app settings and metadata
  versions/      # migration revision files
alembic.ini      # Alembic CLI configuration
```

### How Alembic Detects Model Changes

1. Models inherit from `Base` in `app/db/base.py`.
2. `migrations/env.py` imports model modules so they are registered in `Base.metadata`.
3. `alembic revision --autogenerate` compares `Base.metadata` with the current DB schema.

## Standard Workflow

### 1. Ensure environment is configured

```bash
cat .env | grep DATABASE_URL
```

Expected format:

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/contacts_db
```

### 2. Ensure PostgreSQL is running

Using Docker (example):

```bash
docker compose ps
# If the database is not running, start the stack from the project root:
docker compose up -d
```

### 3. Generate a migration

```bash
alembic revision --autogenerate -m "create contacts table"
```

### 4. Review generated revision

```bash
cat migrations/versions/<revision_file>.py
```

Check that both functions exist and look correct:

- `upgrade()`
- `downgrade()`

### 5. Apply migrations

```bash
alembic upgrade head
```

### 6. Verify result

```sql
SELECT *
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'contacts';
```

## Useful Alembic Commands

```bash
alembic current
alembic history --oneline
alembic upgrade head
alembic upgrade +1
alembic downgrade -1
alembic downgrade base
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`

Run Alembic from repository root.

### `Could not locate a Python environment`

Activate the virtual environment before running commands.

### `could not connect to server: Connection refused`

Check:

1. PostgreSQL is running.
2. `DATABASE_URL` is correct.
3. Host, port, and credentials are valid.
