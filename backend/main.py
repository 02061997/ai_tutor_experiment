# backend/main.py
# Corrected Version (Added /static mount BEFORE / mount)

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status # Added HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # Ensure this is imported
import os # Ensure this is imported
import traceback # Added for explicit traceback printing in custom handler

# Import configuration settings
from backend.core.config import settings

# Import the main API router for v1
from backend.api.v1.router import api_router_v1

# Import database initialization/cleanup functions
from backend.db.database import init_db, close_db, engine
# Ensure models are imported before init_db() if create_db_and_tables is called inside it
from backend.db import models



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle application startup and shutdown events.
    - Initializes database connection pool and creates tables on startup.
    - Closes database connection pool on shutdown.
    """
    print("Application startup...")
    db_url = str(engine.url)
    if db_url.startswith("sqlite"):
        db_path = db_url.split("///")[-1]
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
                print(f"Creating data directory: {db_dir}")
                os.makedirs(db_dir, exist_ok=True)

    await init_db()
    yield
    print("Application shutdown...")
    await close_db()


# Create the FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# --- Add a custom exception handler to log tracebacks ---
# This is a basic example; you might want more sophisticated logging
@app.exception_handler(Exception) # Catches all Exceptions, including AttributeError
async def generic_exception_handler(request, exc):
    print(f"--- UNHANDLED EXCEPTION CAUGHT IN main.py ({type(exc).__name__}) ---")
    print(f"Request: {request.method} {request.url}")
    traceback.print_exc() # Print the full traceback to the console
    print("-----------------------------------------")
    # Return a standard 500 response
    # Ensure you import HTTPException and status from fastapi
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"An internal server error occurred: {exc}" # You might want a more generic message in production
    )
# --- End Custom Exception Handler ---


# Configure CORS (Cross-Origin Resource Sharing)
# (Keep existing CORS configuration as before)
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
        print("Warning: No CORS origins set. Allowing all origins for local development.")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

# --- Define/Include Routes BEFORE Mounting Static Files ---

# Define the simple /ping route FIRST
@app.get("/ping")
async def simple_ping():
    print("DEBUG: Reached /ping endpoint")
    return {"message": "pong"}
print("DEBUG: Added /ping route directly to app")

# Include the Version 1 API router next
app.include_router(api_router_v1, prefix=settings.API_V1_STR)
print(f"DEBUG: Included API router at prefix {settings.API_V1_STR}")


# --- Mount Static Files ---
# Mount specific assets like PDFs first
static_assets_dir = "static"
if os.path.isdir(static_assets_dir):
    # **** ADDED THIS MOUNT for /static path ****
    app.mount("/static", StaticFiles(directory=static_assets_dir), name="static_assets")
    print(f"Serving static assets from: {os.path.abspath(static_assets_dir)} at /static")
else:
        print(f"Warning: Static assets directory '{static_assets_dir}' not found.")


# Mount the frontend app at the root path LAST
static_frontend_dir = "frontend"
if os.path.isdir(static_frontend_dir):
    app.mount("/", StaticFiles(directory=static_frontend_dir, html=True), name="static_frontend")
    print(f"Serving static frontend from: {os.path.abspath(static_frontend_dir)} at /")
else:
        print(f"Warning: Static frontend directory '{static_frontend_dir}' not found.")


# --- Root Endpoint (Optional Fallback - Less likely to be hit now) ---
@app.get("/")
async def read_app_root():
        print("DEBUG: Reached Root / endpoint")
        return {"message": f"Welcome to {settings.PROJECT_NAME}. API is at {settings.API_V1_STR}/docs"}


# --- For Development: Running the App ---
# uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000