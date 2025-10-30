# Integration Testing Guide

This document describes the integration test suite for the manufacturer API integration.

## Overview

Integration tests verify that adapters and routers work correctly with **real vendor API responses**. Unlike unit tests that use mock data, integration tests:

- Make actual API calls to the manufacturer API
- Verify adapter parsing with real response structures
- Test end-to-end data flow
- Validate error handling with real error responses
- Ensure config-driven behavior works correctly

## Prerequisites

### 1. Environment Variables

Add to your `.env` file:

```bash
# Manufacturer API Credentials
MANUFACTURER_API_BASE_URL=http://180.167.106.70:9337
MANUFACTURER_API_USERNAME=your_username
MANUFACTURER_API_PASSWORD=your_password

# Test Configuration (optional)
TEST_DEVICE_ID=cam001  # Device ID that exists in manufacturer system
```

### 2. Test Device

Ensure you have a test device ID that:
- Exists in the manufacturer system
- Has some GPS data (for GPS tests)
- Is accessible with your credentials

## Running Tests

### Run All Tests

```bash
cd pythonProject
source .venv/bin/activate
python test_integration.py
```

### Run Specific Category

```bash
# Authentication tests
python test_integration.py --category auth

# GPS adapter tests
python test_integration.py --category gps

# Device adapter tests
python test_integration.py --category devices

# End-to-end flow tests
python test_integration.py --category e2e

# Config integration tests
python test_integration.py --category config
```

## Test Categories

### 1. Authentication Tests (`auth`)

Tests manufacturer API authentication:
- ✅ Successful login
- ✅ Token persistence across requests

**Note**: Login happens automatically on first API call.

### 2. GPS Adapter Tests (`gps`)

Tests GPS adapter with real API responses:
- ✅ Request building
- ✅ Response parsing (latest GPS)
- ✅ Track history parsing

**Note**: Some tests may be skipped if test device has no GPS data.

### 3. Device Adapter Tests (`devices`)

Tests device adapter with real API responses:
- ✅ Device list parsing
- ✅ Device states parsing

### 4. End-to-End Flow Tests (`e2e`)

Tests complete data flow:
- ✅ GPS data flow: request → API → adapter → DTO
- ✅ Error handling with invalid devices

### 5. Config Integration Tests (`config`)

Tests config-driven behavior:
- ✅ Response paths read from YAML config
- ✅ Success codes read from YAML config

## Test Output

Tests print colored output:

- ✅ **Green**: Test passed
- ⚠️ **Yellow**: Test skipped (no data or API error)
- ❌ **Red**: Test failed

### Example Output

```
============================================================
Manufacturer API Integration Tests
============================================================
Test Device ID: cam001
Base URL: http://180.167.106.70:9337
Profile: default

============================================================
Authentication Tests
============================================================

▶ Login to manufacturer API... ✅ PASSED
▶ Token persistence across requests... ✅ PASSED

============================================================
GPS Adapter Integration Tests
============================================================

▶ Build latest GPS request... ✅ PASSED
▶ Parse latest GPS response... ⚠️  SKIPPED  (No GPS data)
▶ Parse track history response... ⚠️  SKIPPED  (No track data)

============================================================
Test Summary
============================================================
Total Tests: 8
✅ Passed: 5
❌ Failed: 0
⏭️  Skipped: 3

Success Rate: 100.0%
```

## Understanding Skipped Tests

Tests are skipped (not failed) when:
- Vendor API returns non-success code (device not found, etc.)
- No data exists for test device (normal for new/test devices)
- API credentials are invalid (should fail, not skip)

**Skipped tests are expected** and don't indicate problems.

## Correlation IDs

All adapter parse methods include correlation IDs in logs:

```
INFO: [gps001] Parsing GPS response for device cam001
```

Use correlation IDs to trace requests through logs:

```bash
# Find all logs for a specific correlation ID
grep "\[gps001\]" server.log

# Find all adapter parsing logs
grep "Parsing.*response" server.log
```

## Troubleshooting

### "Missing manufacturer API credentials"

**Problem**: Tests fail immediately with credential error.

**Solution**: Add credentials to `.env`:
```bash
MANUFACTURER_API_USERNAME=your_username
MANUFACTURER_API_PASSWORD=your_password
```

### "Invalid token" errors

**Problem**: Authentication fails even with correct credentials.

**Solution**: 
1. Verify credentials are correct
2. Check network connectivity to manufacturer API
3. Verify base URL is correct

### All GPS tests skipped

**Problem**: GPS tests skip with "No GPS data found".

**Solution**: This is normal if:
- Test device has no recent GPS data
- Device is offline
- Device ID is incorrect

Use a device that has active GPS tracking.

### Tests timeout

**Problem**: Tests hang or timeout.

**Solution**:
1. Check network connectivity
2. Verify manufacturer API is accessible
3. Check if API is rate-limiting requests

## Continuous Integration

For CI/CD, integration tests should:

1. **Use test credentials**: Separate test account in manufacturer system
2. **Mock vendor responses**: Use recorded responses for reliability
3. **Run in parallel**: Separate test categories can run concurrently
4. **Skip flaky tests**: Mark environment-dependent tests as "optional"

### Example CI Configuration

```yaml
# GitHub Actions example
- name: Run Integration Tests
  env:
    MANUFACTURER_API_USERNAME: ${{ secrets.TEST_API_USERNAME }}
    MANUFACTURER_API_PASSWORD: ${{ secrets.TEST_API_PASSWORD }}
    TEST_DEVICE_ID: test_device_001
  run: |
    python test_integration.py
```

## Next Steps

After integration tests pass:

1. ✅ Verify adapters handle real vendor responses correctly
2. ✅ Confirm data transformations (coordinates, timestamps) work
3. ✅ Test error handling with real error responses
4. ✅ Validate config-driven behavior

Then proceed to:
- Production deployment
- Performance testing
- Load testing

## Related Tests

- **Unit Tests**: `test_adapters.py` - Test adapters with mock data
- **Syntax Tests**: `test_syntax.py` - Validate Python syntax
- **E2E Tests**: `test_e2e.py` - Test API endpoints end-to-end

