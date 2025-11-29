# Endpoint Spec: Create Forwarding Policy

- Endpoint name (internal): forwarding_policy_create
- Vendor URL path: /api/v1/forwarding/policy/create
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - name: string (required, 1-32)
  - configs: PolicyConfig (required) — see Forwarding Policy Config
  - description: string (optional, <=255)
  - companyId: int64 (required)
  - platformId: int64 (required)
  - configType: int64 (required) — 1 by company, 2 by device
  - forwardCompanyId: int64 (required when configType=1)
  - deviceIds: array<string> (required when configType=2)
- Response success: code == 200; data.id is new policy ID

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/forwarding/policy/create' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "name": "GPS Forwarding Policy",
  "configs": {"msgIds": [1,3], "gps": {"coordinateType": 1, "parseAdditionalInfo": true}},
  "companyId": 1,
  "platformId": 1,
  "configType": 1,
  "forwardCompanyId": 100
}'
```
