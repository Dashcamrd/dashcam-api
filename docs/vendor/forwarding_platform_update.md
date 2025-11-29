# Endpoint Spec: Update Forwarding Platform

- Endpoint name (internal): forwarding_platform_update
- Vendor URL path: /api/v1/forwarding/platform/update
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - id: int64 (required)
  - name: string (optional)
  - configs: PlatformConfig (optional) — see Forwarding Platform Config
  - description: string (optional)
- Response success: code == 200

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/forwarding/platform/update' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "id": 1,
  "name": "Updated Platform",
  "configs": {"protocol":1, "httpConfig": {"url": "https://api.updated.com/forwarding", "timeout": 60}},
  "description": "Updated"
}'
```
