import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Try to load development first, but if system has APP_ENV=production, load that
env_file = ".env.production" if os.environ.get("APP_ENV") == "production" else ".env.development"
load_dotenv(env_file)

APP_ENV = os.getenv("APP_ENV", "development")

if APP_ENV == "production":
    # Production uses Postgres (set DATABASE_URL in .env.production)
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
else:
    # Local uses SQLite
    SQLALCHEMY_DATABASE_URL = "sqlite:///./local_dev.db"

# connect_args is needed only for SQLite
connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
