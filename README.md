# Numina Backend (FastAPI)

REST API for Numina: JWT auth, user profiles, tests, and AI refinement (scheduled via **arq** + Redis). Uses **Neon Postgres** and optional **OpenAI** for insights.

## Setup

1. **Environment**  
   Copy `.env.example` to `.env` and set:
   - `DATABASE_URL` — Neon Postgres; use **async** driver: `postgresql+asyncpg://user:pass@host/db?sslmode=require`
   - `REDIS_URL` — Redis for caching and job queue (e.g. `redis://localhost:6379/0`)
   - `JWT_SECRET_KEY` — long random string for signing JWTs
   - Optional: `OPENAI_API_KEY` for AI refinement; `STRIPE_*` when you add payments

2. **Database (create tables on Neon)**  
   Put `DATABASE_URL` in **`backend/.env`** (same file the API uses). Then, from the **backend** directory, run migrations so the `users` table (and others) are created in your Neon database:
   ```bash
   cd backend
   .venv/bin/python -m alembic upgrade head
   ```
   You should see: `Alembic: running migrations against Neon database (neon.tech)`.  
   If you get "relation \"users\" does not exist", the API is using a different database than the one you migrated—ensure there is only one `backend/.env` and that the app is started from the backend directory (or that no other `DATABASE_URL` overrides it).

3. **Run API**  
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   - API: http://localhost:8000  
   - Docs: http://localhost:8000/docs  
   - Health: http://localhost:8000/api/v1/health  

4. **Run worker (AI refinement)**  
   In a separate terminal, with Redis and DB available:
   ```bash
   uv run python -m app.worker.run_worker
   ```
   Submitting a test enqueues a job; the worker refines the result with AI (or fallback) and saves it. Clients poll `GET /api/v1/tests/results/{id}` until `status` is `completed`.

## Authentication (JWT, no Clerk)

- **Register:** `POST /api/v1/auth/register` — body: `{ "email", "password", "name", "birth_year", "birth_month", "birth_day", "birth_time?", "birth_place?" }` → `{ "access_token", "token_type": "bearer" }`
- **Login:** `POST /api/v1/auth/login` — `{ "email", "password" }` → same token
- **Protected routes:** header `Authorization: Bearer <access_token>`
- **Profile:** `GET /api/v1/users/me` (cached), `PATCH /api/v1/users/me` (name, birth_year, birth_month, birth_day, birth_time, birth_place)

## Tests

- **Catalog:** `GET /api/v1/tests` — list of tests (cached)
- **Submit:** `POST /api/v1/tests/submit` — body: `{ "test_id", "test_title", "category", "answers" }` → `{ "result_id", "status": "pending_ai" }`; AI job is enqueued
- **Results:** `GET /api/v1/tests/results?test_id=` — list current user’s results; `GET /api/v1/tests/results/{id}` — single result (poll for completion)

## Caching and AI

- **Redis** used for: test list cache, user profile cache, AI result cache (by test/user/answer hash), and per-user daily AI request count (rate limit).
- **AI:** Worker runs with strict token limit and daily per-user cap; results are cached to avoid duplicate OpenAI calls. Without `OPENAI_API_KEY`, a fallback response is stored.
