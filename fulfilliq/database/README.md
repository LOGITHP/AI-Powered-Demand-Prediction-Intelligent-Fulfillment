# Database

PostgreSQL is the Docker Compose database. Local development defaults to SQLite through the async aiosqlite driver.

SQLAlchemy models live in backend/app/models. Use Alembic from the backend directory to apply the initial schema migration:

    alembic upgrade head

The API creates missing tables at startup for a first-run demo. The seed service only runs when the database has no stores and does not remove existing data.
