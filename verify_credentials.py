"""
Quick credential verification script.
Tests if manufacturer API credentials are configured correctly.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_credentials():
    """Check if credentials are configured"""
    print("🔍 Checking Manufacturer API Credentials")
    print("=" * 50)
    print()
    
    base_url = os.getenv("MANUFACTURER_API_BASE_URL")
    username = os.getenv("MANUFACTURER_API_USERNAME")
    password = os.getenv("MANUFACTURER_API_PASSWORD")
    device_id = os.getenv("TEST_DEVICE_ID", "cam001")
    
    all_good = True
    
    # Check base URL
    if not base_url:
        print("❌ MANUFACTURER_API_BASE_URL: NOT SET")
        print("   Default: http://180.167.106.70:9337")
        all_good = False
    else:
        print(f"✅ MANUFACTURER_API_BASE_URL: {base_url}")
    
    # Check username
    if not username:
        print("❌ MANUFACTURER_API_USERNAME: NOT SET")
        print("   Required for authentication")
        all_good = False
    else:
        print(f"✅ MANUFACTURER_API_USERNAME: {username}")
    
    # Check password
    if not password:
        print("❌ MANUFACTURER_API_PASSWORD: NOT SET")
        print("   Required for authentication")
        all_good = False
    else:
        print(f"✅ MANUFACTURER_API_PASSWORD: *** (configured)")
    
    # Check device ID
    print(f"{'✅' if device_id else '⚠️ '} TEST_DEVICE_ID: {device_id}")
    if not device_id:
        print("   Using default: cam001")
    
    print()
    
    if not all_good:
        print("⚠️  Missing required credentials!")
        print()
        print("To configure:")
        print("1. Run: ./setup_test_credentials.sh")
        print("2. Or edit .env file manually")
        print()
        print("Required in .env:")
        print("  MANUFACTURER_API_BASE_URL=http://180.167.106.70:9337")
        print("  MANUFACTURER_API_USERNAME=your_username")
        print("  MANUFACTURER_API_PASSWORD=your_password")
        print("  TEST_DEVICE_ID=cam001  # Optional")
        return False
    
    # Try to connect
    print("🧪 Testing connection...")
    try:
        from services.manufacturer_api_service import ManufacturerAPIService
        
        api = ManufacturerAPIService()
        print(f"✅ API Service initialized")
        print(f"   Base URL: {api.base_url}")
        print(f"   Username: {api.username}")
        print(f"   Password: {'***' if api.password else 'NOT SET'}")
        
        # Try a simple API call to verify credentials work
        print()
        print("🔐 Testing authentication...")
        try:
            result = api.get_user_device_list({"page": 1, "pageSize": 1})
            code = result.get("code")
            
            if code in [200, 0]:
                print("✅ Authentication successful!")
                print(f"   API returned code: {code}")
                return True
            elif code == 1008:
                print("⚠️  Token expired or invalid")
                print("   This might be normal - token will refresh automatically")
                return True
            else:
                print(f"⚠️  API returned code: {code}")
                print(f"   Message: {result.get('message', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize API service: {e}")
        return False

if __name__ == "__main__":
    success = check_credentials()
    sys.exit(0 if success else 1)

