# Endpoint Spec: Query System Configuration

- Endpoint name (internal): syscfg_get
- Vendor URL path: /api/v1/stat/config/system/getConfig
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - name: string (required)
  - deviceIdList: array<string> (optional)
  - pageArg: object (required)
    - page: uint32 (required)
    - pageSize: uint32 (required)
- Response success condition: code == 200
- Response data path: data.configs[], data.pageArg

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/stat/config/system/getConfig' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "name": "Alarm Config 1",
  "deviceIdList": ["device1", "device2"],
  "pageArg": { "page": 1, "pageSize": 10 }
}'
```
