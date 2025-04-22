# backend/db/database.py
# Corrected to use SQLModel's AsyncSession

from typing import AsyncGenerator
# Import SQLModel's AsyncSession instead of SQLAlchemy's directly for sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel # Import SQLModel base class

from backend.core.config import settings # Import settings to get DATABASE_URL

# Define the database URL from settings
DATABASE_URL = settings.DATABASE_URL

# Create the asynchronous engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True, # Log SQL queries - set to False in production
    future=True, # Use the future SQLAlchemy 2.0 style
    connect_args={"check_same_thread": False} # Needed for SQLite sync backend with SQLAlchemy
)

# Create an asynchronous sessionmaker using SQLModel's AsyncSession
AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession, # <-- Use SQLModel's AsyncSession here
    expire_on_commit=False,
    autoflush=False,
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an asynchronous database session.
    Ensures the session is closed after the request is finished.
    (This function is likely defined in deps.py now, kept here for reference/completeness)
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
    # Ensure models are imported so metadata is populated
    from backend.db import models # Make sure models are imported

    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Uncomment for development reset
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Database tables created (if they didn't exist).")

# Optional: Function to initialize DB connection pool during startup
async def init_db():
    """
    Initializes the database connection pool and creates tables.
    """
    print(f"Initializing database connection for: {DATABASE_URL}")
    await create_db_and_tables() # Create tables on startup


# Optional: Function to close DB connection pool during shutdown
async def close_db():
    """
    Closes the database connection pool.
    """
    print("Closing database connection pool.")
    await engine.dispose()