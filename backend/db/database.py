"""
Database Configuration - Async SQLAlchemy

Supports SQLite by default and Postgres (e.g. Neon) via DATABASE_URL.
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
IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_NEON = (not IS_SQLITE) and ("neon.tech" in DATABASE_URL or os.getenv("DB_PROVIDER", "").lower() == "neon")

# Fix asyncpg SSL parameter compatibility with Neon/Postgres
if not IS_SQLITE and "sslmode=" in DATABASE_URL:
    # Convert sslmode=require to ssl=require for asyncpg compatibility
    DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")
    # Remove channel_binding parameter which asyncpg doesn't support
    DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "").replace("?channel_binding=require", "").replace("channel_binding=require&", "").replace("channel_binding=require", "")


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Create async engine
if IS_SQLITE:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL query logging
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Required for SQLite with async
    )
else:
    pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "15"))
    connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
    command_timeout = int(os.getenv("DB_COMMAND_TIMEOUT", "30"))
    statement_cache_size = int(os.getenv("DB_STATEMENT_CACHE_SIZE", "0" if IS_NEON else "100"))

    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL query logging
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_use_lifo=True,
        connect_args={
            "timeout": connect_timeout,
            "command_timeout": command_timeout,
            "statement_cache_size": statement_cache_size,
        },
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

        # Add high-impact indexes used by ownership checks and hot query paths.
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_slides_session_number ON slides (session_id, slide_number)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_slide_versions_slide_version ON slide_versions (slide_id, version_number)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages (session_id, created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_user_created ON presentation_history (user_id, created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_otp_lookup ON email_otp (email, purpose, used_at, created_at)"))

        if IS_SQLITE:
            # Lightweight schema migration for existing SQLite databases
            result = await conn.execute(text("PRAGMA table_info(users)"))
            user_columns = [row[1] for row in result.fetchall()]
            if user_columns and "avatar_url" not in user_columns:
                await conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url TEXT"))

    if IS_SQLITE:
        print(f"✓ Database initialized at {DATABASE_PATH}")
    else:
        print("✓ Database initialized using external DATABASE_URL")


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
