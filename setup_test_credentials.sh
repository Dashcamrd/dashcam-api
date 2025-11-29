#!/bin/bash
# Setup script for integration test credentials

echo "🔧 Integration Test Credentials Setup"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
    else
        touch .env
        echo "✅ Created empty .env file"
    fi
    echo ""
fi

echo "Current credentials status:"
echo "---------------------------"

# Check each required variable
BASE_URL=$(grep "MANUFACTURER_API_BASE_URL" .env | cut -d '=' -f2 | tr -d ' ' || echo "")
USERNAME=$(grep "MANUFACTURER_API_USERNAME" .env | cut -d '=' -f2 | tr -d ' ' || echo "")
PASSWORD=$(grep "MANUFACTURER_API_PASSWORD" .env | cut -d '=' -f2 | tr -d ' ' || echo "")
DEVICE_ID=$(grep "TEST_DEVICE_ID" .env | cut -d '=' -f2 | tr -d ' ' || echo "")

if [ -z "$BASE_URL" ]; then
    echo "❌ MANUFACTURER_API_BASE_URL: NOT SET"
else
    echo "✅ MANUFACTURER_API_BASE_URL: $BASE_URL"
fi

if [ -z "$USERNAME" ]; then
    echo "❌ MANUFACTURER_API_USERNAME: NOT SET"
else
    echo "✅ MANUFACTURER_API_USERNAME: $USERNAME"
fi

if [ -z "$PASSWORD" ]; then
    echo "❌ MANUFACTURER_API_PASSWORD: NOT SET"
else
    echo "✅ MANUFACTURER_API_PASSWORD: *** (hidden)"
fi

if [ -z "$DEVICE_ID" ]; then
    echo "⚠️  TEST_DEVICE_ID: NOT SET (will use default: cam001)"
else
    echo "✅ TEST_DEVICE_ID: $DEVICE_ID"
fi

echo ""
echo "Required credentials:"
echo "--------------------"
echo "1. MANUFACTURER_API_BASE_URL - API base URL (default: http://180.167.106.70:9337)"
echo "2. MANUFACTURER_API_USERNAME - Your API username"
echo "3. MANUFACTURER_API_PASSWORD - Your API password"
echo "4. TEST_DEVICE_ID - Device ID for testing (optional, default: cam001)"
echo ""

# Interactive setup
read -p "Do you want to configure credentials now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    
    # Base URL
    if [ -z "$BASE_URL" ]; then
        read -p "Enter MANUFACTURER_API_BASE_URL [http://180.167.106.70:9337]: " url
        url=${url:-http://180.167.106.70:9337}
        echo "MANUFACTURER_API_BASE_URL=$url" >> .env
        echo "✅ Added MANUFACTURER_API_BASE_URL"
    fi
    
    # Username
    if [ -z "$USERNAME" ]; then
        read -p "Enter MANUFACTURER_API_USERNAME: " username
        if [ ! -z "$username" ]; then
            echo "MANUFACTURER_API_USERNAME=$username" >> .env
            echo "✅ Added MANUFACTURER_API_USERNAME"
        fi
    fi
    
    # Password
    if [ -z "$PASSWORD" ]; then
        read -s -p "Enter MANUFACTURER_API_PASSWORD: " password
        echo
        if [ ! -z "$password" ]; then
            echo "MANUFACTURER_API_PASSWORD=$password" >> .env
            echo "✅ Added MANUFACTURER_API_PASSWORD"
        fi
    fi
    
    # Device ID
    if [ -z "$DEVICE_ID" ]; then
        read -p "Enter TEST_DEVICE_ID [cam001]: " device
        device=${device:-cam001}
        echo "TEST_DEVICE_ID=$device" >> .env
        echo "✅ Added TEST_DEVICE_ID"
    fi
    
    echo ""
    echo "✅ Credentials configured!"
    echo ""
    echo "Next steps:"
    echo "1. Verify credentials: python test_integration.py --category auth"
    echo "2. Run full tests: python test_integration.py"
else
    echo ""
    echo "To configure manually, edit .env file and add:"
    echo "  MANUFACTURER_API_BASE_URL=http://180.167.106.70:9337"
    echo "  MANUFACTURER_API_USERNAME=your_username"
    echo "  MANUFACTURER_API_PASSWORD=your_password"
    echo "  TEST_DEVICE_ID=cam001"
fi

