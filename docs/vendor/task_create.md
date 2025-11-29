# Endpoint Spec: Create Text Delivery Task

- Endpoint name (internal): task_create
- Vendor URL path: /api/v1/textDelivery/createTask
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - name: string (required)
  - content: string (required)
  - contentTypes: array<string> (required) — ["1" (screen), "2" (voice)]
  - conditions: object (required)
    - deviceIds: array<string> (required)
  - status: uint32 (required) — 0 closed, 1 open (default: closed)
  - scheduleAt: uint32 seconds (optional) — default immediate
  - deadline: uint32 seconds (optional) — default scheduleAt + 14 days
  - ignoreLowPower: uint32 (optional) — 0 wait online, 1 deliver in low power
- Response success condition: code == 200
- Response data path: data.id

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/textDelivery/createTask' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "name": "test",
  "content": "1231",
  "contentTypes": ["1", "2"],
  "status": 1,
  "conditions": {"deviceIds": ["17721028810"]}
}'
```
