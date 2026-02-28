"""
Database Configuration - Async SQLAlchemy with SQLite

Provides async database connection and session management.
"""
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool


# Database file path
DATABASE_DIR = os.getenv("DATABASE_DIR", "storage")
DATABASE_FILE = os.getenv("DATABASE_FILE", "ai_ppt.db")
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)

# Ensure storage directory exists when using file-based SQLite
os.makedirs(DATABASE_DIR, exist_ok=True)

# Database connection string (can be overridden in environment)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DATABASE_PATH}")


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Create async engine
# For SQLite, we need special configuration to allow async access
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Required for SQLite with async
)

# Async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        # Import models to ensure they're registered
        from db import models  # noqa
        await conn.run_sync(Base.metadata.create_all)

        # Lightweight schema migration for existing SQLite databases
        result = await conn.execute(text("PRAGMA table_info(users)"))
        user_columns = [row[1] for row in result.fetchall()]
        if user_columns and "avatar_url" not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url TEXT"))

    print(f"✓ Database initialized at {DATABASE_PATH}")


async def get_db() -> AsyncSession:
    """
    Dependency for getting database sessions.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """
    Get a database session for use outside of FastAPI dependencies.
    
    Remember to close the session when done.
    """
    return async_session_maker()
