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
        
        # Import migration function
        from add_device_id_column import add_device_id_column
        add_device_id_column()
        
        print("✅ Database migrations completed")
    except Exception as e:
        print(f"⚠️  Database migration warning: {str(e)}")
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


