# Endpoint Spec: Get Task List

- Endpoint name (internal): task_get_list
- Vendor URL path: /api/v1/textDelivery/getTaskList
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - page: uint32 (required) — starts at 1
  - pageSize: uint32 (required)
  - startTime: uint64 seconds (optional)
  - endTime: uint64 seconds (optional)
  - status: uint32 (optional) — 0 all, 1 in progress, 2 completed
- Response success condition: code == 200
- Response data path: data.total, data.list[] (or tasks[] per response table; example shows list in data)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/textDelivery/getTaskList' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "page": 1,
  "pageSize": 10,
  "startTime": 1714016000,
  "endTime": 1714016117,
  "status": 0
}'
```
