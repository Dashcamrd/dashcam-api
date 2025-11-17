# Endpoint Spec: Get Task Details

- Endpoint name (internal): task_get_details
- Vendor URL path: /api/v1/textDelivery/getTaskById
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - id: int64 (required) — task ID (docs show `taskId` name; example body used `id`. Confirm exact key.)
- Response success condition: code == 200
- Response data path: data.task
- Task fields include: id, name, content, contentTypes[], scheduleAt, deadline, totals, state/status, operator info, company info, createdAt/updatedAt, conditions.deviceIds[], ignoreLowPower

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/textDelivery/getTaskById' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{ "id": 5428 }'
```
