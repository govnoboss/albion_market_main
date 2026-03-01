from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer, text
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


class PurchaseSession(Base):
    """Telemetry: one row per buyer session from any client"""
    __tablename__ = "purchase_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, index=True)  # Dedup key
    license_key = Column(String, index=True)               # FK → licenses.key
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    city = Column(String, nullable=True)
    items_bought = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)
    total_profit_est = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    client_ip = Column(String, nullable=True)


class PurchaseItem(Base):
    """Per-item breakdown within a purchase session"""
    __tablename__ = "purchase_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True)        # FK → purchase_sessions.session_id
    item_name = Column(String, index=True)
    qty = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)
    profit_est = Column(Integer, default=0)


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
