# Endpoint Spec: Delete Forwarding Policy

- Endpoint name (internal): forwarding_policy_delete
- Vendor URL path: /api/v1/forwarding/policy/delete
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - ids: array<int64> (required)
- Response success: code == 200

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/forwarding/policy/delete' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{"ids":[1,2,3]}'
```
