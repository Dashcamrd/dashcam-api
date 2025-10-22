"""
Migration script to add device_id column to users table
"""
from database import engine
from sqlalchemy import text

def add_device_id_column():
    """Add device_id column to users table"""
    try:
        with engine.connect() as connection:
            # Check if column already exists
            result = connection.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'dashcamdb' 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'device_id'
            """))
            
            if result.fetchone() is None:
                # Add the column
                connection.execute(text("ALTER TABLE users ADD COLUMN device_id VARCHAR(100) NULL"))
                connection.commit()
                print("✅ Added device_id column to users table")
            else:
                print("ℹ️  device_id column already exists")
                
    except Exception as e:
        print(f"❌ Error adding device_id column: {str(e)}")

if __name__ == "__main__":
    print("🔄 Adding device_id column to users table...")
    add_device_id_column()
    print("✅ Migration complete!")
