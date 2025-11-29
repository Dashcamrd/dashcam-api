import os
import sqlalchemy
from sqlalchemy import create_engine, text

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/dashcam")

def migrate_db():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        try:
            print("🔄 Attempting to add 'is_admin' column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("✅ Column 'is_admin' added (or already exists).")
        except Exception as e:
            print(f"⚠️ Error adding column: {e}")

if __name__ == "__main__":
    migrate_db()

