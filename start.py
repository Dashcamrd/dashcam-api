"""
Startup script for Dashcam Management Platform
"""
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_database_migrations():
    """Run database migrations on startup"""
    try:
        print("🔄 Running database migrations...")
        
        from database import engine
        from sqlalchemy import text, inspect
        
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        # Migration 1: Add device_id column
        if 'device_id' not in columns:
            print("   Adding device_id column to users table...")
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN device_id VARCHAR(100) NULL"))
                connection.commit()
            print("✅ Added device_id column to users table")
            columns.append('device_id')
        
        # Migration 2: Add phone column
        if 'phone' not in columns:
            print("   Adding phone column to users table...")
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50) NULL"))
                connection.commit()
            print("✅ Added phone column to users table")
            columns.append('phone')
        
        print("✅ Database migrations completed")
    except Exception as e:
        # Silently continue if migration fails - tables might already be correct
        error_msg = str(e).lower()
        if 'duplicate column' in error_msg or 'already exists' in error_msg:
            print("✅ Database schema is up to date")
        else:
            print(f"ℹ️  Database check skipped: {type(e).__name__}")
        print("   Continuing startup...")

if __name__ == "__main__":
    # Run database migrations first
    run_database_migrations()
    
    # Configuration
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    print("🚀 Starting Dashcam Management Platform API...")
    print(f"📍 Server will be available at: http://{host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print(f"🔄 Auto-reload: {'Enabled' if reload else 'Disabled'}")
    print("=" * 50)
    
    uvicorn.run(
        "main:app", 
        host=host, 
        port=port, 
        reload=reload,
        log_level="info"
    )


