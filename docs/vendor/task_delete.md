# Endpoint Spec: Delete Task

- Endpoint name (internal): task_delete
- Vendor URL path: /api/v1/textDelivery/deleteTask
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - id: int64 (required) — task ID
- Response success condition: code == 200
- Response data path: data (empty)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/textDelivery/deleteTask' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "id": 5428
}'
```

## Sample Success Response (from docs)
```json
{ "code": 200, "message": "success", "ts": 1714016117 }
```
