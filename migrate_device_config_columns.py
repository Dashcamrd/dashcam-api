"""
Database Migration Script - Add Device Auto-Configuration Columns

This script adds the following columns to the devices table:
- configured: VARCHAR(10), default 'no' - Whether device has been configured
- config_last_attempt: DATETIME - Last configuration attempt timestamp
- config_attempts: INT, default 0 - Number of configuration attempts
- last_online_at: DATETIME - When device came online (for 3-min delay)

Run this script once to update the database schema.
"""

import sys
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def migrate():
    """Add auto-configuration columns to devices table"""
    engine = create_engine(DATABASE_URL)
    
    # SQL statements for different database types
    alterations = [
        # Add 'configured' column
        """
        ALTER TABLE devices 
        ADD COLUMN IF NOT EXISTS configured VARCHAR(10) DEFAULT 'no';
        """,
        # Add 'config_last_attempt' column
        """
        ALTER TABLE devices 
        ADD COLUMN IF NOT EXISTS config_last_attempt TIMESTAMP NULL;
        """,
        # Add 'config_attempts' column
        """
        ALTER TABLE devices 
        ADD COLUMN IF NOT EXISTS config_attempts INTEGER DEFAULT 0;
        """,
        # Add 'last_online_at' column
        """
        ALTER TABLE devices 
        ADD COLUMN IF NOT EXISTS last_online_at TIMESTAMP NULL;
        """
    ]
    
    # Alternative SQL for MySQL (doesn't support IF NOT EXISTS for columns)
    mysql_alterations = [
        ("configured", "ALTER TABLE devices ADD COLUMN configured VARCHAR(10) DEFAULT 'no';"),
        ("config_last_attempt", "ALTER TABLE devices ADD COLUMN config_last_attempt DATETIME NULL;"),
        ("config_attempts", "ALTER TABLE devices ADD COLUMN config_attempts INT DEFAULT 0;"),
        ("last_online_at", "ALTER TABLE devices ADD COLUMN last_online_at DATETIME NULL;"),
    ]
    
    print("🔄 Starting migration: Adding auto-configuration columns to devices table...")
    print(f"📡 Database URL: {DATABASE_URL[:50]}...")
    
    with engine.connect() as conn:
        # Detect database type
        is_mysql = "mysql" in DATABASE_URL.lower()
        
        if is_mysql:
            print("📦 Detected MySQL database")
            # For MySQL, check if column exists first
            for column_name, sql in mysql_alterations:
                try:
                    # Check if column exists
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) as cnt 
                        FROM information_schema.COLUMNS 
                        WHERE TABLE_NAME = 'devices' 
                        AND COLUMN_NAME = '{column_name}'
                    """))
                    row = result.fetchone()
                    exists = row[0] > 0 if row else False
                    
                    if exists:
                        print(f"   ⏭️  Column '{column_name}' already exists, skipping")
                    else:
                        conn.execute(text(sql))
                        conn.commit()
                        print(f"   ✅ Added column '{column_name}'")
                except Exception as e:
                    if "Duplicate column" in str(e):
                        print(f"   ⏭️  Column '{column_name}' already exists, skipping")
                    else:
                        print(f"   ❌ Error adding column '{column_name}': {e}")
        else:
            print("📦 Detected PostgreSQL database")
            # PostgreSQL supports IF NOT EXISTS
            for sql in alterations:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"   ⏭️  Column already exists, skipping")
                    else:
                        print(f"   ❌ Error: {e}")
    
    print("\n✅ Migration completed!")
    print("\nNew columns added to devices table:")
    print("  - configured: Tracks if device has been auto-configured ('yes'/'no')")
    print("  - config_last_attempt: Timestamp of last configuration attempt")
    print("  - config_attempts: Number of configuration attempts made")
    print("  - last_online_at: Timestamp when device came online")
    print("\nThe auto-configuration service will now:")
    print("  1. Detect when devices come online")
    print("  2. Wait 3 minutes for stable connection")
    print("  3. Send configuration command")
    print("  4. Mark device as configured on success")
    print("  5. Retry every 5 minutes on failure")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

