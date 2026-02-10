from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
import datetime
import uuid
import os

# SQLite database file - use persistent volume on fly.io, local path for dev
# On fly.io, /data is a mounted persistent volume
if os.path.exists("/data"):
    DATABASE_PATH = "/data/licenses.db"
else:
    # Local development - use path relative to this file
    BASE_DIR = Path(__file__).resolve().parent
    DATABASE_PATH = str(BASE_DIR / "licenses.db")

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Enable Write-Ahead Logging (WAL) for better concurrency
from sqlalchemy import text
with engine.connect() as connection:
    connection.execute(text("PRAGMA journal_mode=WAL;"))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class License(Base):
    __tablename__ = "licenses"
    
    key = Column(String, primary_key=True, index=True)
    hwid = Column(String, nullable=True, default=None)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, nullable=True)
    last_ip = Column(String, nullable=True)

    @staticmethod
    def generate_key():
        """Generates a random license key XXXX-XXXX-XXXX-XXXX"""
        return str(uuid.uuid4()).upper()

def init_db():
    Base.metadata.create_all(bind=engine)
    
    try:
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(licenses)"))
            columns = [row[1] for row in result.fetchall()]
            
            if "last_seen" not in columns:
                print("Migrating DB: Adding 'last_seen' column...")
                conn.execute(text("ALTER TABLE licenses ADD COLUMN last_seen TIMESTAMP"))
            
            if "last_ip" not in columns:
                 print("Migrating DB: Adding 'last_ip' column...")
                 conn.execute(text("ALTER TABLE licenses ADD COLUMN last_ip VARCHAR"))

            conn.commit()
            print("Migration successful.")
    except Exception as e:
        print(f"Migration check failed: {e}")
