# Endpoint Spec: Get Task Execution Results

- Endpoint name (internal): task_get_results
- Vendor URL path: /api/v1/textDelivery/getTaskResult
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema (all optional unless specified):
  - id: int64 (optional) — task ID; when omitted, query all
  - name: string (optional) — fuzzy by task name
  - page: uint32 (optional) — starts at 1
  - pageSize: uint32 (optional)
  - type: uint32 (optional) — 0 all, 1 success, 2 failed, 3 offline
  - deviceId: string (optional) — filter by device
- Response success condition: code == 200
- Response data path: data.total, data.list[]
- Key fields (list[]): id, deviceId, setupAt, versions, replyMsgID, replyResult, plateNumber, status, content, contentTypes[], task{...}, settingStatus

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/textDelivery/getTaskResult' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "id": 5428,
  "page": 1,
  "pageSize": 10,
  "type": 0,
  "deviceId": "17721028810"
}'
```
