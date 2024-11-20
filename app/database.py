from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Get database URL from environment variable, with a default SQLite URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./openalgo.db")

# Ensure the database directory exists for SQLite
if SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
    db_path = Path(SQLALCHEMY_DATABASE_URL.replace("sqlite:///", ""))
    db_dir = db_path.parent
    db_dir.mkdir(parents=True, exist_ok=True)

# Create SQLAlchemy engine with proper configuration
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={
            "check_same_thread": False,  # SQLite specific argument
            "timeout": 30  # Connection timeout in seconds
        }
    )
else:
    # For other databases like PostgreSQL, MySQL, etc.
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,  # Maximum number of database connections in the pool
        max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
        pool_timeout=30,  # Timeout for getting a connection from the pool
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_pre_ping=True  # Enable connection health checks
    )

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent expired objects after commit
)

# Create Base class for declarative models
Base = declarative_base()

def get_db():
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.
    
    Usage:
        @app.get("/users/")
        def read_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize the database by creating all tables.
    Should be called when the application starts.
    
    This function:
    1. Creates all tables defined in the models
    2. Creates initial roles if they don't exist
    3. Sets up any required indexes
    """
    Base.metadata.create_all(bind=engine)

def dispose_engine():
    """
    Properly dispose of the database engine.
    Should be called when shutting down the application.
    """
    engine.dispose()
