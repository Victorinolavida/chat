# Chat

A real-time chat application with user registration, JWT authentication, and
WebSocket messaging. The backend is a Flask API with a SQLite database; the
frontend is a Vite + React single-page app.

## Features

- User registration and login (`username`, `email`, `password`).
- Unique email and username, passwords hashed with bcrypt.
- JWT-based authentication; the frontend session survives page reloads until the
  token expires.
- Real-time messaging over WebSockets (Socket.IO), with message history persisted
  in the database and loaded on reload.
- Messages are scoped by an optional `conversation_id`; when it is `null`, the
  message belongs to the general chat.
- DTOs are kept separate from the database models.
- Database migrations with Flask-Migrate (Alembic).
- Backend unit/integration tests with pytest.

## Tech stack

**Backend**

- Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- Flask, Flask-SQLAlchemy, Flask-Migrate (Alembic), Flask-SocketIO
- Flask-JWT-Extended, bcrypt, Pydantic, python-dotenv
- SQLite

**Frontend**

- Vite, React 19, socket.io-client

## Project structure

```
app/
  __init__.py          # create_app factory
  config.py            # environment-based configuration
  extensions.py        # db, migrate, jwt, socketio instances
  models/              # SQLAlchemy models (User, Message)
  dtos/                # Pydantic DTOs (request/response schemas)
  services/            # business logic (users, messages)
  routes/              # HTTP blueprints (auth, messages)
  sockets/             # Socket.IO event handlers
  responses.py         # helpers for JSON/validation error responses
migrations/            # Alembic migration scripts
tests/                 # pytest suite
frontend/              # Vite + React SPA
run.py                 # application entrypoint
Makefile               # common commands
```

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/), Node.js (v20+), and GNU Make.

```bash
# 1. Backend dependencies
make install

# 2. Environment file
cp .env.example .env        # then edit the secrets and port

# 3. Create/update the database
make db-upgrade

# 4. Run the backend (HTTP + WebSocket)
make run
```

In a second terminal:

```bash
make frontend-install
make frontend-dev
```

The frontend runs on `http://localhost:5173` and proxies API and WebSocket
requests to the backend.

## Configuration

Backend settings are read from `.env` (see `.env.example`):

| Variable         | Default                     | Description                                  |
| ---------------- | --------------------------- | -------------------------------------------- |
| `SECRET_KEY`     | `change-me-in-production`   | Flask secret key                             |
| `JWT_SECRET_KEY` | `change-me-in-production`   | JWT signing key                              |
| `DATABASE_URL`   | `sqlite:///<instance>/chat.db` | SQLAlchemy database URI                   |
| `HOST`           | `0.0.0.0`                   | Bind host                                    |
| `PORT`           | `5000`                      | Bind port                                    |
| `DEBUG`          | `true`                      | Enable debug/reload                          |
| `SOCKETIO_PATH`  | `/ws`                       | WebSocket endpoint path                      |

Frontend settings are read from `frontend/.env` (see `frontend/.env.example`):

| Variable          | Default                 | Description                       |
| ----------------- | ----------------------- | --------------------------------- |
| `VITE_API_TARGET` | `http://localhost:5000` | Backend target for the dev proxy  |

> macOS note: port `5000` is used by AirPlay Receiver. Set `PORT=8100` (and
> `VITE_API_TARGET=http://localhost:8100`) to avoid the conflict.

## API

All responses are JSON. Errors use a consistent shape:
`{ "error": "...", "message": "..." }`.

### `GET /health`

Returns `{ "status": "ok" }`.

### `POST /auth/register`

Body:

```json
{ "username": "victor", "email": "victor@example.com", "password": "supersecret" }
```

`201 Created` with the created user, `409 Conflict` if the email or username is
taken, `422` on validation errors.

### `POST /auth/login`

Body:

```json
{ "email": "victor@example.com", "password": "supersecret" }
```

`200 OK` with `{ "access_token": "...", "user": { ... } }`, or `401` on invalid
credentials.

### `GET /messages`

Requires `Authorization: Bearer <token>`.

Query parameters:

- `conversation_id` (optional) — omit or leave empty for the general chat.
- `limit` (optional) — default `50`, max `200`.

```json
{
  "conversation_id": null,
  "messages": [
    {
      "id": "01a13c96-90a9-733a-8230-55dcbe14b6bb",
      "from_user_id": 1,
      "from_username": "victor",
      "to_user_id": null,
      "conversation_id": null,
      "body": "hello world",
      "created_at": "2026-10-14T22:44:22.825215Z"
    }
  ]
}
```

## WebSocket

Socket.IO is served at `/ws`. Connect with the JWT in the auth payload:

```js
import { io } from 'socket.io-client'

const socket = io({ path: '/ws', auth: { token: accessToken } })
```

The server refuses the connection if the token is missing, invalid, or expired.

**Client → server**

- `chat:message` — `{ "message": "hello" }`

**Server → client**

- `chat:message` — a new message:
  `{ id, from_user_id, from_username, to_user_id, conversation_id, body, created_at }`
- `chat:system` — a user joined: `{ message, username, timestamp }`
- `chat:error` — a validation/auth error: `{ error, message }`

## Data model

- **User** — `id`, `username` (unique), `email` (unique), `password_hash`,
  `created_at`.
- **Message** — `id` (UUIDv7), `from_user_id`, `to_user_id` (nullable),
  `conversation_id` (nullable → general chat), `body`, `created_at`.

## Testing

```bash
make test          # uv run pytest -q
make frontend-lint # oxlint
```

## Make targets

Run `make help` for the full list. Common ones:

| Target             | Description                                    |
| ------------------ | ---------------------------------------------- |
| `install`          | Install/sync backend dependencies             |
| `run`              | Start the backend (HTTP + WebSocket)          |
| `test`             | Run the backend test suite                    |
| `db-migrate m=".."`| Autogenerate a migration                      |
| `db-upgrade`       | Apply pending migrations                      |
| `db-reset`         | Recreate the database and apply migrations    |
| `frontend-install` | Install frontend dependencies                 |
| `frontend-dev`     | Start the frontend dev server                 |
| `frontend-build`   | Build the frontend for production             |
| `frontend-lint`    | Lint the frontend                             |
| `shell`            | Open a Flask shell                            |
| `routes`           | List registered HTTP routes                   |
