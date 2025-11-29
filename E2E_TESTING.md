# End-to-End Testing Guide

This guide explains how to run end-to-end tests to verify the adapter integration with the actual API.

## Quick Start

### Option 1: Automated (Recommended)
```bash
cd pythonProject
source .venv/bin/activate
./run_e2e_tests.sh
```

This script will:
1. Check if server is running
2. Start server if needed (in background)
3. Wait for server to be ready
4. Run all E2E tests
5. Stop server when done

### Option 2: Manual

**Step 1: Start the server**
```bash
cd pythonProject
source .venv/bin/activate
python start.py
```

**Step 2: In another terminal, run tests**
```bash
cd pythonProject
source .venv/bin/activate
python test_e2e.py
```

## What Gets Tested

### 1. Server Health Check
- Verifies server is running and accessible
- Checks `/health` endpoint

### 2. Authentication
- Tests `/auth/login` endpoint
- Retrieves JWT token for subsequent requests
- Uses test credentials from environment or defaults

### 3. GPS Endpoints (with Adapters)
- `GET /gps/latest/{device_id}` - Verifies adapter parses response correctly
  - Checks for normalized fields (device_id, latitude, longitude, timestamp_ms)
  - Verifies coordinate conversion (1e6 → decimal)
  - Verifies timestamp conversion (seconds → milliseconds)
  
- `GET /gps/devices` - Verifies device list with GPS status
  - Checks adapter integration
  - Verifies DTO structure

### 4. Device Endpoints (with Adapters)
- `GET /gps/states/{device_id}` - Verifies device state adapter
  - Checks ACC state parsing
  - Verifies timestamp conversion

### 5. Media Endpoints
- Tests skipped by default (requires actual device connection)
- Can be enabled manually in test script

### 6. Log Analysis
- Verifies correlation IDs appear in logs
- Checks request tracing functionality

### 7. Direct Adapter Integration
- Tests adapters directly (without HTTP)
- Verifies request building and response parsing

## Test Configuration

### Environment Variables

Set these in `.env` or export before running:

```bash
# Test user credentials (optional - will use defaults if not set)
export TEST_INVOICE="INV2024001"
export TEST_PASSWORD="customer123"

# Device ID for testing (optional)
export TEST_DEVICE_ID="cam001"
```

### Test Settings

Edit `test_e2e.py` to customize:

```python
BASE_URL = "http://127.0.0.1:8000"  # Change if server runs on different port
TEST_TIMEOUT = 30  # Request timeout in seconds
```

## Expected Results

### ✅ Success Indicators

- All adapters imported successfully
- DTOs have correct structure
- Responses include normalized fields
- Coordinates in decimal degrees (not 1e6 scaled)
- Timestamps in milliseconds (not seconds)
- Correlation IDs appear in logs

### ⚠️ Expected Warnings

These are normal and don't indicate failure:

- **"Device not accessible"** - Device may not be assigned to test user
- **"No GPS data found"** - Vendor API may not have data for test device
- **"No correlation IDs found"** - Logs may be empty if no requests made yet

### ❌ Failure Indicators

- Server not running
- Authentication failures (invalid credentials)
- Syntax errors in adapters
- Incorrect data transformations
- Missing correlation IDs after making requests

## Troubleshooting

### Server Won't Start

1. Check if port 8000 is in use:
   ```bash
   lsof -i :8000
   ```

2. Check database connection:
   ```bash
   # Verify DATABASE_URL in .env
   cat .env | grep DATABASE_URL
   ```

3. Check manufacturer API credentials:
   ```bash
   cat .env | grep MANUFACTURER_API
   ```

### Authentication Fails

1. Create a test user:
   ```bash
   # Use admin endpoint or database
   python setup_initial_data.py
   ```

2. Or use existing credentials from your database

### Tests Fail with 403 Errors

- Device may not be assigned to test user
- Check device assignments in database
- Use admin endpoint to assign device to user

### No GPS Data

- Vendor API may not have data for test device
- Verify device ID exists in manufacturer system
- Check manufacturer API connectivity

## Advanced Testing

### Test Specific Endpoint

```python
# In test_e2e.py, comment out other tests and focus on one:
def main():
    token = test_authentication()
    test_gps_endpoints(token, "your_device_id")
```

### Test with Real Device

1. Update `TEST_DEVICE_ID` with real device ID
2. Ensure device is assigned to test user
3. Verify device has recent GPS data in vendor system

### Test Correlation IDs

```bash
# After running tests, check logs
tail -f server.log | grep "\[.*\]"

# Or search for specific correlation ID
grep "\[a3f2c1d4\]" server.log
```

## Integration with CI/CD

For automated testing in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run E2E Tests
  run: |
    source .venv/bin/activate
    python start.py &
    sleep 5
    python test_e2e.py
```

## Next Steps

After successful E2E tests:

1. ✅ Adapters work correctly
2. ✅ DTOs have proper structure
3. ✅ Data transformations are correct
4. ✅ Correlation IDs are working

You can now:
- Deploy to staging/production
- Add more comprehensive integration tests
- Monitor logs for correlation IDs in production

