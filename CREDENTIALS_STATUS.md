# Credentials Status

## ✅ Current Configuration

Your `.env` file has:

```
MANUFACTURER_API_BASE_URL=http://180.167.106.70:9337
MANUFACTURER_API_USERNAME=mono1
MANUFACTURER_API_PASSWORD=7977b3237b2809c59da6f3e51300ddf0
```

## ⚠️ Authentication Issue

The API is returning: **"password err, code: 1006"**

This means the password authentication is failing. Possible reasons:

1. **Password hash vs plaintext**: The password in `.env` appears to be a hash. The manufacturer API might require the **plaintext password**, not a hash.

2. **Password expired/changed**: The password may have been changed in the manufacturer system.

3. **Incorrect password**: The stored password may be incorrect.

## 🔧 How to Fix

### Option 1: Update Password in .env

If you know the correct plaintext password:

```bash
# Edit .env file
nano .env

# Update the password line:
MANUFACTURER_API_PASSWORD=your_actual_plaintext_password
```

### Option 2: Test with Different Password

Try testing with the actual password:

```bash
# Temporarily test with different password
export MANUFACTURER_API_PASSWORD="your_password_here"
python verify_credentials.py
```

### Option 3: Get Fresh Credentials

If you don't have the correct password:

1. Contact your manufacturer API administrator
2. Request new credentials or password reset
3. Update `.env` with the new password

## ✅ Once Fixed

After updating credentials, verify:

```bash
python verify_credentials.py
```

You should see:
- ✅ Authentication successful!
- ✅ API returned code: 200

Then you can run integration tests:

```bash
python test_integration.py
```

## 📝 Notes

- **Password Security**: Make sure `.env` is in `.gitignore` (it should be)
- **Never commit credentials**: Don't push `.env` to version control
- **TEST_DEVICE_ID**: Currently not set, will use default `cam001`

## 🧪 Quick Test

To test if credentials work, try:

```bash
# Test authentication only
python test_integration.py --category auth
```

This will verify if your credentials can successfully authenticate with the manufacturer API.

