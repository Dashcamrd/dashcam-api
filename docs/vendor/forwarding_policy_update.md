# Endpoint Spec: Update Forwarding Policy

- Endpoint name (internal): forwarding_policy_update
- Vendor URL path: /api/v1/forwarding/policy/update
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - id: int64 (required)
  - name: string (optional)
  - configs: PolicyConfig (optional)
  - description: string (optional)
  - platformId: int64 (optional)
  - configType: int64 (optional) — 1 by company, 2 by device
  - forwardCompanyId: int64 (required when configType=1)
  - deviceIds: array<string> (required when configType=2)
- Response success: code == 200

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/forwarding/policy/update' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "id": 1,
  "name": "Updated GPS Policy",
  "configs": {"msgIds":[1,3], "gps": {"coordinateType":2, "parseAdditionalInfo": false}},
  "description": "Updated description"
}'
```
