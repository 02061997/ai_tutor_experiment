# backend/db/database.py

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel # Import SQLModel base class

from backend.core.config import settings # Import settings to get DATABASE_URL

# Define the database URL from settings
DATABASE_URL = settings.DATABASE_URL

# Create the asynchronous engine
# connect_args={"check_same_thread": False} is specific to SQLite
# to allow connections from different threads (FastAPI uses threads).
# For async (`aiosqlite`), this might not be strictly necessary but doesn't hurt.
# echo=True logs SQL statements, useful for debugging during development.
engine = create_async_engine(
    DATABASE_URL,
    echo=True, # Log SQL queries - set to False in production
    future=True, # Use the future SQLAlchemy 2.0 style
    connect_args={"check_same_thread": False} # Needed for SQLite sync, potentially useful for async too
)

# Create an asynchronous sessionmaker
# expire_on_commit=False prevents attributes from being expired
# after commit, which can be useful in async contexts.
AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False, # Disable autoflush for async
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an asynchronous database session.
    Ensures the session is closed after the request is finished.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit() # Commit changes if everything was successful
        except Exception:
            await session.rollback() # Rollback in case of errors
            raise
        finally:
            await session.close() # Ensure session is closed

async def create_db_and_tables():
    """
    Creates all database tables defined by SQLModel metadata.
    Should be called during application startup (e.g., in a lifespan event).
    """
    # Note: Import all models that inherit from SQLModel HERE before calling create_all!
    # This is crucial so that SQLModel's metadata knows about the tables.
    # We will define these models in `backend/db/models.py` later.
    # Example placeholder:
    # from backend.db import models # Uncomment when models.py exists

    async with engine.begin() as conn:
        # In SQLAlchemy 2.0, create_all should be called on the metadata
        # Drop all tables (useful for development, REMOVE FOR PRODUCTION)
        # await conn.run_sync(SQLModel.metadata.drop_all)
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Database tables created (if they didn't exist).")

# Optional: Function to initialize DB connection pool during startup
async def init_db():
    """
    Initializes the database connection pool.
    May be called during application startup lifespan event.
    """
    # The engine is already created, this function might just ensure connectivity
    # or perform initial checks if needed. For SQLite, it's often simple.
    print(f"Initializing database connection for: {DATABASE_URL}")
    # You could potentially test the connection here if desired
    # async with engine.connect() as connection:
    #     pass
    await create_db_and_tables() # Create tables on startup


# Optional: Function to close DB connection pool during shutdown
async def close_db():
    """
    Closes the database connection pool.
    Called during application shutdown lifespan event.
    """
    print("Closing database connection pool.")
    await engine.dispose()