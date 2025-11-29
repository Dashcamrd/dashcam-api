# Endpoint Spec: Logout

- Endpoint name (internal): auth_logout
- Vendor URL path: /api/v1/user/logout
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required) — token from Login
- Auth details: token required in header `X-Token`
- Query params: none
- Request body schema: none
- Response success condition: code == 200
- Response data path: data (empty object)
- Field mapping to DTOs: N/A
- Pagination: none
- Error codes and meanings: Not specified in HTML (confirm with vendor docs)

## Sample Request (from docs)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/user/logout' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>'
```

## Sample Success Response (from docs)
```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "ts": 1714016117
}
```
