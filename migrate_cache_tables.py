"""
Migration script to create device_cache and alarms tables.

Run this script to add the new tables for data forwarding support.

Usage:
    python migrate_cache_tables.py
"""

from database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Create the device_cache and alarms tables"""
    
    # SQL for device_cache table
    device_cache_sql = """
    CREATE TABLE IF NOT EXISTS device_cache (
        id SERIAL PRIMARY KEY,
        device_id VARCHAR(100) UNIQUE NOT NULL,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        speed DOUBLE PRECISION,
        direction INTEGER,
        altitude DOUBLE PRECISION,
        address TEXT,
        acc_status BOOLEAN DEFAULT FALSE,
        is_online BOOLEAN DEFAULT FALSE,
        gps_time TIMESTAMP,
        last_online_time TIMESTAMP,
        updated_at TIMESTAMP DEFAULT NOW(),
        extra_data TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_device_cache_device_id ON device_cache(device_id);
    CREATE INDEX IF NOT EXISTS idx_device_cache_updated_at ON device_cache(updated_at);
    """
    
    # SQL for alarms table
    alarms_sql = """
    CREATE TABLE IF NOT EXISTS alarms (
        id SERIAL PRIMARY KEY,
        device_id VARCHAR(100) NOT NULL,
        alarm_type INTEGER NOT NULL,
        alarm_type_name VARCHAR(100),
        alarm_level INTEGER DEFAULT 1,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        speed DOUBLE PRECISION,
        alarm_time TIMESTAMP NOT NULL,
        alarm_data TEXT,
        is_read BOOLEAN DEFAULT FALSE,
        is_acknowledged BOOLEAN DEFAULT FALSE,
        acknowledged_by INTEGER,
        acknowledged_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_alarms_device_id ON alarms(device_id);
    CREATE INDEX IF NOT EXISTS idx_alarms_alarm_time ON alarms(alarm_time);
    CREATE INDEX IF NOT EXISTS idx_alarms_is_read ON alarms(is_read);
    """
    
    try:
        with engine.connect() as conn:
            # Create device_cache table
            logger.info("Creating device_cache table...")
            conn.execute(text(device_cache_sql))
            conn.commit()
            logger.info("✅ device_cache table created successfully")
            
            # Create alarms table
            logger.info("Creating alarms table...")
            conn.execute(text(alarms_sql))
            conn.commit()
            logger.info("✅ alarms table created successfully")
            
            # Verify tables exist
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name IN ('device_cache', 'alarms')
            """))
            tables = [row[0] for row in result]
            logger.info(f"✅ Verified tables exist: {tables}")
            
        logger.info("🎉 Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate()

