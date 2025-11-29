# Endpoint Spec: Login

- Endpoint name (internal): auth_login
- Vendor URL path: /api/v1/user/login
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
- Auth details: none (returns token)
- Query params: none
- Request body schema:
  - username: string (required)
  - password: string (required) — MD5 32-bit lowercase hash
  - progVersion: string (required) — e.g., "0.0.1"
  - platform: int (required) — 1=web, 2=android, 3=ios
  - model: string (optional in example) — e.g., "web"
- Response success condition: code == 200
- Response data path: data
- Field mapping to DTOs: N/A (auth-only; extract token for header `X-Token`)
- Pagination: none
- Error codes and meanings: Not specified in HTML (confirm with vendor docs)

## Sample Request (from docs)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/user/login' \
--header 'Content-Type: application/json' \
--data '{
    "username": "superman",
    "password": "84d961568a65073a3bcf0eb216b2a576",
    "model": "web",
    "progVersion": "0.0.1",
    "platform": 3
}'
```

## Sample Success Response (from docs)
```json
{
  "code": 200,
  "message": "success",
  "ts": 1735883673,
  "data": {
    "userId": 1,
    "username": "superman",
    "companyId": 1,
    "company": "superman",
    "token": "<JWT_TOKEN>"
  }
}
```

## Notes
- Use returned `data.token` as `X-Token` for subsequent requests.
- Password must be md5 hashed before request.
