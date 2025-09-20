# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is rDrama, a Reddit-like discussion forum application built with Flask and SQLAlchemy. The application consists of a Python backend with a React-based chat component.

## Tech Stack

- **Backend**: Python 3.10, Flask, SQLAlchemy, Redis, PostgreSQL
- **Frontend**: Jinja2 templates, vanilla JavaScript, React (chat component only)
- **Package Management**: Poetry (Python), Yarn (JavaScript/chat)
- **Database**: PostgreSQL with Alembic migrations

## Common Development Commands

### Python/Backend

```bash
# Install dependencies
poetry install

# Run tests
./util/test.py

# Run database migrations
python3 -m flask db upgrade

# Run flask commands
python3 -m flask [command]
# OR
./util/command_flask.py [command]
```

## Architecture Overview

### Application Entry Point
- `files/__main__.py` - Main Flask application setup, configures services (THEMOTTE vs CHAT), database connections, Redis cache, rate limiting

### Core Structure
- `files/routes/` - HTTP route handlers organized by feature area
  - `allroutes.py` - Request/response handlers shared across services
  - Major route modules: `posts.py`, `comments.py`, `login.py`, `front.py`, `search.py`
  - `admin/` - Administrative functionality routes

- `files/classes/` - SQLAlchemy ORM models
  - Key models: `User`, `Submission` (posts), `Comment`
  - Warning: Uses wildcard imports internally - be careful with dependencies

- `files/helpers/` - Utility functions and configurations
  - `config/` - Configuration constants and environment variables

- `files/templates/` - Jinja2 templates for server-side rendering

- `files/assets/` - Static assets (CSS, JS, images)

- `chat/` - Separate React application for real-time chat functionality

### Database
- Migrations in `migrations/` directory managed by Alembic
- PostgreSQL database with extensive use of SQLAlchemy ORM
- Redis for caching and rate limiting

### Service Modes
The application can run in different service modes (defined in `files/helpers/config/const.py`):
- `THEMOTTE` - Main forum functionality
- `CHAT` - Chat service only

### Important Patterns
1. **Imports**: Many files use wildcard imports (`from files.classes import *`). Be careful when modifying imports as it can break unrelated parts of the codebase.

2. **Database Sessions**: Uses SQLAlchemy scoped sessions (`db_session`) configured in `__main__.py`

3. **Authentication**: Session-based authentication with Redis backing

4. **Rate Limiting**: Configured via Flask-Limiter with Redis storage

5. **Templates**: Server-side rendering with Jinja2, client-side JavaScript for interactivity

## Testing

Tests are located in `files/tests/` and use pytest. Run all tests with:
```bash
./util/test.py
```

Key test fixtures are defined in `files/tests/fixture_*.py` files.

## Development Environment

The application uses environment variables for configuration. These can be set in:
- `bootstrap/site_env` - Site-specific configuration
- `.env` - Local overrides (takes precedence)

Key environment variables include:
- `SITE_ID` - Site identifier
- `DATABASE_URL` - PostgreSQL connection string
- `CACHE_REDIS_URL` - Redis connection string
- `SECRET_KEY` - Flask secret key
- `ENFORCE_PRODUCTION` - Set to false for development