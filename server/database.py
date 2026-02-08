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
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class License(Base):
    __tablename__ = "licenses"
    
    key = Column(String, primary_key=True, index=True)
    hwid = Column(String, nullable=True, default=None)  # None = Unbound (New Key)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    @staticmethod
    def generate_key():
        """Generates a random license key XXXX-XXXX-XXXX-XXXX"""
        return str(uuid.uuid4()).upper()

def init_db():
    Base.metadata.create_all(bind=engine)
