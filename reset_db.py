from database import engine, Base
# Ensure models are imported so tables are registered in metadata
from models.user_db import UserDB  # noqa: F401
from models.device_db import DeviceDB  # noqa: F401

if __name__ == "__main__":
	print("⚠️  Dropping all tables (users, devices, etc.)...")
	Base.metadata.drop_all(bind=engine)
	print("✅ Dropped.")
	print("🛠  Creating tables...")
	Base.metadata.create_all(bind=engine)
	print("✅ Schema created.")
