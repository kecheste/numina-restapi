# Numina AI Rest API

## Authentication

The API uses **JWT (PyJWT)** and **passlib (bcrypt)** for authentication (no Clerk).

- **Register:** `POST /api/v1/auth/register` — body: `{ "email": "...", "password": "..." }` → returns `{ "access_token": "...", "token_type": "bearer" }`.
- **Login:** `POST /api/v1/auth/login` — same body → same token response.
- **Protected routes:** send `Authorization: Bearer <access_token>`.
- **Current user:** `GET /api/v1/users/me` — requires a valid Bearer token.

Configure via `.env`: `JWT_SECRET_KEY`, `JWT_ALGORITHM` (default `HS256`), `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`. See `.env.example`.

## Database

Run migrations: `alembic upgrade head` (from backend directory, with `DATABASE_URL` set).
