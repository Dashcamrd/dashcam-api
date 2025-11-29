# Endpoint Spec: Update Forwarding Platform Status

- Endpoint name (internal): forwarding_platform_update_status
- Vendor URL path: /api/v1/forwarding/platform/updateStatus
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - id: int64 (required)
  - status: int (required) — 0 disabled, 1 enabled
- Response success: code == 200

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/forwarding/platform/updateStatus' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{"id":1,"status":0}'
```
