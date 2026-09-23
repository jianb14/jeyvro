# JEYVRO Backend

Django 5 + Django REST Framework + PostgreSQL. Governed by
[CONVENTIONS.md](CONVENTIONS.md) and `../.cline/PROJECT_CONTEXT.md`.

## Local setup

1. **Python venv** (already created at `%LOCALAPPDATA%\jeyvro-venv` — outside
   OneDrive on purpose, to avoid file-lock/sync issues):

   ```powershell
   py -m venv "$env:LOCALAPPDATA\jeyvro-venv"
   & "$env:LOCALAPPDATA\jeyvro-venv\Scripts\python.exe" -m pip install -r requirements.txt
   ```

2. **Environment variables** — copy `.env.example` to `.env` and fill real
   values. Every variable is documented there. Never commit the real `.env`
   (PROJECT_CONTEXT C7).

3. **PostgreSQL 16** — install locally (winget:
   `PostgreSQL.PostgreSQL.16`), create the dev database:

   ```powershell
   & 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -U postgres -c "CREATE DATABASE jeyvro;"
   ```

4. **Migrate + run** (dev server on port 8000 — the Vite proxy targets it):

   ```powershell
   & "$env:LOCALAPPDATA\jeyvro-venv\Scripts\python.exe" manage.py migrate
   & "$env:LOCALAPPDATA\jeyvro-venv\Scripts\python.exe" manage.py runserver
   ```

5. **Verify:** open `http://127.0.0.1:8000/api/v1/health` — expected
   `{"status":"ok","service":"jeyvro-backend","database":"ok"}`.

## Tests

```powershell
& "$env:LOCALAPPDATA\jeyvro-venv\Scripts\python.exe" -m pytest -q
```

pytest-django creates an isolated test database automatically; foundation
tests also pass without a running server.
