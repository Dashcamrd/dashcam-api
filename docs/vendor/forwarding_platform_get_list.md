# Endpoint Spec: Get Forwarding Platform List

- Endpoint name (internal): forwarding_platform_get_list
- Vendor URL path: /api/v1/forwarding/platform/getList
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - page: int64 (required, starts at 1)
  - pageSize: int64 (required)
  - name: string (optional, fuzzy)
  - status: array<int> (optional) — 0 disabled, 1 enabled
  - companyId: int64 (optional)
  - companyName: string (optional)
- Response success: code == 200; data.total, data.platforms[]

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/forwarding/platform/getList' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{"page":1,"pageSize":10}'
```
