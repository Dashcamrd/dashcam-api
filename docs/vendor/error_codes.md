# Vendor API Error Codes Reference

This document lists all error codes returned by the manufacturer API. Note that the API returns HTTP 200 for both success and error cases, with the actual status indicated in the `code` field of the JSON response.

## Common Error Codes

| HTTP Status | Error Code | Description | Note |
|-------------|------------|-------------|------|
| 200 | 200 | Request successful | - |
| 200 | 500 | System error | Internal server error |
| 200 | 400 | Parameter validation error | Invalid request parameters |
| 200 | 401 | Unauthorized, missing authentication header | Missing authentication information in request header |
| 200 | 1003 | User does not exist | User account not found |
| 200 | 1004 | User disabled | User account is disabled |
| 200 | 1005 | User expired | User account has expired |
| 200 | 1006 | Incorrect password | Password verification failed |
| 200 | 1007 | Request rate limit | Request frequency exceeds limit |
| 200 | 1008 | Token expired | Token has expired, please login again to get new token |
| 200 | 1009 | Insufficient permissions | User lacks operation permission |
| 200 | 1010 | Operation forbidden | Current operation is forbidden |
| 200 | 1011 | Verification code error | Incorrect verification code |
| 200 | 1012 | Query field does not exist | Requested query field not found |
| 200 | 1013 | Query record does not exist | No records match the conditions |

## User and Permission Error Codes

| HTTP Status | Error Code | Description | Note |
|-------------|------------|-------------|------|
| 200 | 1020 | Username already exists | Duplicate username when creating user |
| 200 | 1021 | Password length limit | Password must be 6-32 characters |
| 200 | 1022 | Password format limit | Password must contain at least two types from numbers, letters, and special characters |
| 200 | 1030 | Role name already exists | Duplicate role name when creating role |
| 200 | 1031 | Role deletion restriction | Cannot delete role with existing users |
| 200 | 1032 | Permission name already exists | Duplicate permission name when creating permission |
| 200 | 1033 | Role does not exist | Specified role not found |

## Company Management Error Codes

| HTTP Status | Error Code | Description | Note |
|-------------|------------|-------------|------|
| 200 | 1040 | Company name already exists | Duplicate company name when creating company |
| 200 | 1041 | Server authorization limit exceeded | Exceeds maximum server authorization limit |
| 200 | 1042 | Parent company authorization limit exceeded | Exceeds parent company authorization limit |
| 200 | 1043 | Company deletion restriction | Company has existing subsidiaries, users, roles, or permissions |
| 200 | 1044 | Current authorization less than authorized vehicles | Authorization amount cannot be less than used amount |
| 200 | 1045 | Company does not exist | Specified company not found |
| 200 | 1046 | Company disabled | Company status is disabled |
| 200 | 1047 | Company expired | Company authorization expired |
| 200 | 1048 | Expiration time limit | Current company expiration time cannot be greater than parent company expiration time |

## Device Related Error Codes

| HTTP Status | Error Code | Description | Note |
|-------------|------------|-------------|------|
| 200 | 1100 | Query exceeds maximum time range limit | Query time range exceeds system limit |
| 200 | 1101 | Device query timeout | Device information query timeout |
| 200 | 1102 | Device offline | Device is currently offline |
| 200 | 1103 | Device in low power mode | Device is in low power mode |
| 200 | 1104 | Device not positioned | Device cannot get location information |
| 200 | 1105 | Device does not exist | Specified device not found |
| 200 | 1106 | Device operation busy | Device operation is busy, please try again later (certain instructions do not support simultaneous multi-user device operations) |
| 200 | 1107 | Device does not support the instruction | Device does not support the instruction |

## Text Delivery Error Codes

| HTTP Status | Error Code | Description | Note |
|-------------|------------|-------------|------|
| 200 | 1200 | Text delivery task does not exist | Specified text delivery task not found |
| 200 | 1201 | Invalid text delivery task status | Current task status does not allow operation |
| 200 | 1202 | Text delivery task running | Task is currently executing |
| 200 | 1203 | Text delivery task not executed | Task has not started execution |
| 200 | 1204 | Text delivery task completed | Task execution completed |
| 200 | 1205 | Invalid text delivery filter conditions | Task filter conditions error |
| 200 | 1206 | Text delivery task limit exceeded | Exceeds maximum task limit |
| 200 | 1207 | Text delivery task failed | Task execution failed |
| 200 | 1208 | Text delivery settings failed | Failed to save task settings |

## Implementation Notes

### Error Response Format

All error responses follow this structure:

```json
{
  "code": <error_code>,
  "message": "<error_description>",
  "ts": <unix_timestamp>,
  "data": {}
}
```

### Important Points

1. **HTTP Status Always 200**: The manufacturer API returns HTTP 200 even for errors. Always check the `code` field in the JSON response.

2. **Token Expiration (1008)**: When encountering code 1008, the client should:
   - Clear cached token
   - Prompt user to re-authenticate
   - Retry the request after obtaining a new token

3. **Rate Limiting (1007)**: Implement exponential backoff when receiving code 1007.

4. **Device Errors (1100-1107)**: These are common for GPS/device operations. Handle gracefully with user-friendly messages.

5. **Common Recovery Actions**:
   - **401, 1008**: Re-authenticate
   - **1007**: Wait and retry with backoff
   - **1102-1107**: Device-specific errors, show user-friendly message
   - **400, 1012**: Invalid request, fix parameters
   - **500**: Server error, log and retry if appropriate

