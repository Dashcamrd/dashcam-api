# Endpoint Spec: Update Task Information

- Endpoint name (internal): task_update_info
- Vendor URL path: /api/v1/textDelivery/updateTaskInfo
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - id: int64 (required) — task ID
  - name: string (optional)
  - content: string (optional)
  - contentTypes: array<string> (optional) — ["1" (screen), "2" (voice)]
  - scheduleAt: uint32 seconds (optional)
  - deadline: uint32 seconds (optional)
- Notes: Only tasks not started can update; tasks in progress cannot modify content/type
- Response success condition: code == 200
- Response data path: none

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/textDelivery/updateTaskInfo' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "id": 5429,
  "name": "Updated task name",
  "content": "Updated delivery content",
  "contentTypes": ["1"]
}'
```
