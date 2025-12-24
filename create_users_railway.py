import requests
import json

# Your Render API URL
API_URL = "https://dashcam-api-latest.onrender.com/auth/register"

# Create Apple Review user
review_user = {
    "invoice_no": "Review",
    "device_id": "18270980023",
    "name": "Apple Review",
    "email": "review@apple.com",
    "password": "Review2025*"
}

print("🍎 Creating Apple Review User in Railway Database via Render API")
print("=" * 60)
print(f"Invoice: {review_user['invoice_no']}")
print(f"Name: {review_user['name']}")
print(f"Email: {review_user['email']}")
print(f"Device ID: {review_user['device_id']}")
print()

try:
    response = requests.post(API_URL, json=review_user)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ User created successfully!")
        print()
        print("📋 Login Credentials for Apple Review:")
        print(f"  Invoice Number: {review_user['invoice_no']}")
        print(f"  Password: {review_user['password']}")
        print()
        print("🔑 Access Token:", result.get('access_token', 'N/A')[:50] + "...")
    else:
        print(f"❌ Error creating user:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

