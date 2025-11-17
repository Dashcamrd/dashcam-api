# Endpoint Spec: Delete System Configuration

- Endpoint name (internal): syscfg_delete
- Vendor URL path: /api/v1/stat/config/system/deleteConfig
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - id: uint64 (required) — configuration ID
- Response success condition: code == 200
- Response data path: data (empty)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/stat/config/system/deleteConfig' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{ "id": 1 }'
```
