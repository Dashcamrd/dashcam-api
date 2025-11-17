# Endpoint Spec: Create Forwarding Platform

- Endpoint name (internal): forwarding_platform_create
- Vendor URL path: /api/v1/forwarding/platform/create
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - name: string (required, 1-32)
  - status: int (required) — 0 disabled, 1 enabled
  - configs: PlatformConfig (required)
    - protocol: int (1 HTTP)
    - httpConfig: { url: string, headers?: map<string,string>, timeout?: int }
  - description: string (optional, <=255)
  - companyId: int64 (required)
- Response success: code == 200; data.id is new platform ID

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/forwarding/platform/create' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "name": "Test Platform",
  "status": 1,
  "configs": {"protocol": 1, "httpConfig": {"url": "https://api.example.com/forwarding", "timeout": 30}},
  "description": "Forwarding platform",
  "companyId": 1
}'
```
