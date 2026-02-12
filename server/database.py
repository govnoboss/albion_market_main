from sqlalchemy import create_engine, Column, String, Boolean, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime
import uuid
import os

# SQLite database file
# Use /data volume in production (set by DATABASE_URL env var in fly.toml)
# Fallback to local ./licenses.db for dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./licenses.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class License(Base):
    __tablename__ = "licenses"
    
    key = Column(String, primary_key=True, index=True)
    hwid = Column(String, nullable=True, default=None) 
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    # New fields
    last_seen = Column(DateTime, nullable=True)
    last_ip = Column(String, nullable=True)

    @staticmethod
    def generate_key():
        """Generates a random license key XXXX-XXXX-XXXX-XXXX"""
        return str(uuid.uuid4()).upper()

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Simple migration: check if columns exist
    with engine.connect() as conn:
        try:
            # Check last_seen
            try:
                conn.execute(text("SELECT last_seen FROM licenses LIMIT 1"))
            except:
                print("Migrating: Adding last_seen column...")
                conn.execute(text("ALTER TABLE licenses ADD COLUMN last_seen DATETIME"))
                
            # Check last_ip
            try:
                conn.execute(text("SELECT last_ip FROM licenses LIMIT 1"))
            except:
                print("Migrating: Adding last_ip column...")
                conn.execute(text("ALTER TABLE licenses ADD COLUMN last_ip VARCHAR"))
        except Exception as e:
            print(f"Migration check failed (maybe table empty or new): {e}")
