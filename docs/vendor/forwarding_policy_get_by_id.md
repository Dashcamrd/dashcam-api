# Endpoint Spec: Get Forwarding Policy Details

- Endpoint name (internal): forwarding_policy_get_by_id
- Vendor URL path: /api/v1/forwarding/policy/getById
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - id: int64 (required)
- Response success: code == 200; data.policy

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/forwarding/policy/getById' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{"id":1}'
```
