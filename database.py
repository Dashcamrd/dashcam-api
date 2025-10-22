from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use environment variable for database URL, fallback to local
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:Alm_123123*@localhost:3306/dashcamdb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
