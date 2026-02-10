import sqlite3
from pathlib import Path

# Path to database
BASE_DIR = Path(__file__).resolve().parent.parent / "server"
DB_PATH = BASE_DIR / "licenses.db"

def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    print(f"Migrating database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(licenses)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "last_ip" not in columns:
            print("Adding 'last_ip' column...")
            cursor.execute("ALTER TABLE licenses ADD COLUMN last_ip VARCHAR")
            conn.commit()
            print("Migration successful.")
        else:
            print("'last_ip' column already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
