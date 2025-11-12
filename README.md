# CommunityHub - Community Event Platform (demo)

## What this demo shows
- FastAPI (async)
- Async SQLAlchemy + Postgres
- Redis caching
- RabbitMQ publish + consume (aio-pika)
- JWT auth
- WebSocket real-time notifications
- Docker + docker-compose local environment

## Quick start
1. Copy `.env.example` to `.env` and edit if needed.
2. Start services:
   ```bash
   # Start all application services (excludes test service)
   docker compose up --build
   
   # Or run in detached mode (background)
   docker compose up -d --build
   ```
3. App runs at: [http://localhost:8001](http://localhost:8001)
4. RabbitMQ management UI: [http://localhost:15672](http://localhost:15672). Credentials: `guest/guest`
5. Redis Commander UI: [http://localhost:8081](http://localhost:8081)
6. Swagger docs: [http://localhost:8001/docs](http://localhost:8001/docs)

### Stopping Services

```bash
# Stop all running services
docker compose down

# Stop and remove volumes (cleans database data)
docker compose down -v
```

### Viewing Service Status and Logs

```bash
# Check which services are running
docker compose ps

# View logs from all services
docker compose logs

# View logs from a specific service
docker compose logs web
docker compose logs worker
docker compose logs db

# Follow logs in real-time
docker compose logs -f web
```

### Services Overview

| Service | Port | Description |
|---------|------|-------------|
| **web** | 8001 | Main FastAPI application |
| **worker** | - | RabbitMQ consumer for background tasks |
| **db** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache |
| **redis-commander** | 8081 | Redis web UI |
| **rabbitmq** | 5672, 15672 | Message broker + management UI |
| **test** | - | Test runner (manual start only) |

**Note**: The test service uses a separate profile and will NOT start with `docker compose up`. See the "Running Tests" section for how to run tests.

## Running Tests

This project includes comprehensive unit and integration tests. Tests run in Docker with PostgreSQL, Redis, and RabbitMQ.

**Important**: The test service is configured with a `testing` profile and will NOT start automatically with `docker compose up`. This keeps your development environment clean and only runs tests when explicitly requested.

### Run All Tests

```bash
# Run all tests with coverage report
docker compose run --rm test

# Run with verbose output
docker compose run --rm test pytest tests/ -v

# Run with detailed output and stop on first failure
docker compose run --rm test pytest tests/ -xvs
```

**Note**: `docker compose run --rm test` automatically:
- Starts required dependencies (PostgreSQL, Redis, RabbitMQ)
- Creates the test database
- Runs the test suite
- Removes the container after completion (`--rm` flag)

### Run Specific Test Categories

```bash
# Run only unit tests
docker compose run --rm test pytest tests/unit/

# Run only integration tests
docker compose run --rm test pytest tests/integration/

# Run tests from a specific file
docker compose run --rm test pytest tests/integration/test_auth.py

# Run a specific test
docker compose run --rm test pytest tests/integration/test_auth.py::TestAuthEndpoints::test_login_success
```

### Test Coverage

```bash
# Generate HTML coverage report (viewable in htmlcov/index.html)
docker compose run --rm test pytest tests/ --cov=app --cov-report=html

# View coverage summary in terminal
docker compose run --rm test pytest tests/ --cov=app --cov-report=term-missing
```

### Test Database

Tests use a separate test database (`communityhub_test`) that is automatically:
- Created before tests run
- Cleaned between each test for isolation
- Dropped and recreated for each test function

**Test Suite Statistics**:
- **Total Tests**: 65 passing, 2 skipped
- **Test Coverage**: ~80%
- **Unit Tests**: 39 (repositories, security, schemas)
- **Integration Tests**: 26 (API endpoints, authentication, authorization)

## Troubleshooting

### Swagger UI Showing Blank Page

If the Swagger documentation at http://localhost:8001/docs shows a blank page, this is likely due to Content Security Policy (CSP) headers blocking external resources. The CSP configuration in `app/middleware/security_headers.py` has been configured to allow Swagger UI assets from `cdn.jsdelivr.net`.

To verify Swagger is working:
```bash
# Check if the docs endpoint returns HTML
curl http://localhost:8001/docs | head -20

# Restart the web container if you recently updated the middleware
docker compose restart web
```

### Database Connection Issues

If you see database connection errors, ensure PostgreSQL is running and the connection string is correct in your `.env` file.

### Redis/RabbitMQ Connection Issues

Ensure all services are running:
```bash
docker compose ps

# If services are down, restart them
docker compose up -d
```

## Database Migrations

This project uses Alembic for database migrations.

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current migration
alembic current
```

### Creating New Migrations

```bash
# Create a new migration (autogenerate from models)
alembic revision --autogenerate -m "Description of changes"

# Create an empty migration
alembic revision -m "Description of changes"
```

**Note**: In Docker, migrations are automatically run at startup. For local development, run migrations manually before starting the app.


## Basic Demo Flow

1. **Register a user:**
   - `POST /api/v1/auth/register`
2. **Login:**
   - `POST /api/v1/auth/login` (get access token)
3. **Authorize in Swagger UI:**
   - Click the "Authorize" button (lock icon) at the top right
   - Paste your access token from the login response
   - Click "Authorize" - the token will be added to all subsequent requests
4. **Create an event:**
   - (organizer role required, use the token)
   - `POST /api/v1/events/`
5. **Connect a websocket:**
   - `ws://localhost:8001/ws/notifications/{user_id}?token=YOUR_ACCESS_TOKEN`
6. **RSVP to an event:**
   - `POST /api/v1/rsvps/` — see websocket push by the notification consumer

### Using Bearer Token Authentication

After logging in, you'll receive an `access_token` in the response. To use protected endpoints:

**In Swagger UI:**
1. Click the "Authorize" button (🔒) at the top right
2. In the "Value" field, paste your access token (just the token, NOT "Bearer token")
3. Click "Authorize" and then "Close"
4. All protected endpoints will now include your token automatically

**In cURL/HTTP clients:**
```bash
# Example: Get current user info
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" http://localhost:8001/api/v1/auth/me

# Example: Create an event (requires organizer role)
curl -X POST http://localhost:8001/api/v1/events/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"title": "Tech Meetup", "description": "Monthly tech meetup", "location": "Downtown", "capacity": 50}'
```

**Note**: The application uses JWT Bearer token authentication, not OAuth2 password flow.


## Notes

- Database migrations are managed with Alembic (see Database Migrations section above).
- Redis is used for caching frequently accessed data (events list and details).
- Worker container listens to RabbitMQ and sends notifications to connected websockets.
