# Endpoint Spec: Get Forwarding Policy List

- Endpoint name (internal): forwarding_policy_get_list
- Vendor URL path: /api/v1/forwarding/policy/getList
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - page: int64 (required)
  - pageSize: int64 (required)
  - name: string (optional, fuzzy)
  - companyId: int64 (optional)
  - companyName: string (optional)
  - platformName: string (optional)
- Response success: code == 200; data.total, data.policies[]

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/forwarding/policy/getList' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{"page":1,"pageSize":10}'
```
