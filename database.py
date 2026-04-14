from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use environment variable for database URL, fallback to local
# Supports both PostgreSQL (Render) and MySQL (local development)
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:Dashcam2024%21@localhost:3306/dashcamdb")

# Convert postgres:// to postgresql:// if needed (Render uses postgres://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# For Render PostgreSQL: Use internal URL when available (faster, more reliable)
INTERNAL_DATABASE_URL = os.getenv("DATABASE_URL_INTERNAL")
if INTERNAL_DATABASE_URL:
    if INTERNAL_DATABASE_URL.startswith("postgres://"):
        INTERNAL_DATABASE_URL = INTERNAL_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    DATABASE_URL = INTERNAL_DATABASE_URL
    print(f"🔗 Using internal database connection")

# Add SSL parameters to PostgreSQL URL if connecting to Render
if DATABASE_URL and DATABASE_URL.startswith("postgresql://") and ".render.com" in DATABASE_URL:
    # Add sslmode parameter to the URL
    separator = "?" if "?" not in DATABASE_URL else "&"
    DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"
    print("🔒 SSL enabled for PostgreSQL connection")

# Create engine with connection pool settings
connect_args = {"connect_timeout": 10}
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    # PostgreSQL-specific settings
    connect_args = {
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    pool_timeout=10,
    connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
