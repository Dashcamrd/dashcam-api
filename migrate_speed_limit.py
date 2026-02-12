"""
Migration: Add speed_limit and last_speed_alert_at columns to user_notification_settings table.
"""
import logging
from sqlalchemy import text
from database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Add speed_limit and last_speed_alert_at columns."""
    
    sql_statements = [
        """
        ALTER TABLE user_notification_settings 
        ADD COLUMN IF NOT EXISTS speed_limit INTEGER DEFAULT NULL;
        """,
        """
        ALTER TABLE user_notification_settings 
        ADD COLUMN IF NOT EXISTS last_speed_alert_at TIMESTAMP DEFAULT NULL;
        """,
    ]
    
    try:
        with engine.connect() as conn:
            for sql in sql_statements:
                logger.info(f"Executing: {sql.strip()[:80]}...")
                conn.execute(text(sql))
                conn.commit()
            
            logger.info("✅ Speed limit migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate()

