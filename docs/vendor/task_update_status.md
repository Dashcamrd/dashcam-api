# Endpoint Spec: Update Task Status

- Endpoint name (internal): task_update_status
- Vendor URL path: /api/v1/textDelivery/updateTaskStatus
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - id: int64 (required) — task ID
  - status: uint32 (required) — 1 In Progress, 2 Completed
- Response success condition: code == 200
- Response data path: none

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/textDelivery/updateTaskStatus' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{ "id": 5429, "status": 2 }'
```
