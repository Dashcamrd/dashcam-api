# Endpoint Spec: Add System Configuration

- Endpoint name (internal): syscfg_add
- Vendor URL path: /api/v1/stat/config/system/addConfig
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - name: string (required)
  - deviceIdList: array<string> (optional)
  - content: object (required)
    - uploadAlarmIdList: array<uint32> (required)
    - alarmRetention: uint32 (required) — days (7-365)
    - uploadAttachmentAlarmIdList: array<uint32> (required)
    - attachmentRetention: uint32 (required) — days (7-365)
- Response success condition: code == 200
- Response data path: data{total, assigned, conflictNodeList[], failNodeList[], successNodeList[]}

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/stat/config/system/addConfig' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "name": "Alarm Config 1",
  "deviceIdList": ["device1", "device2"],
  "content": {
    "uploadAlarmIdList": [1,2,3],
    "alarmRetention": 30,
    "uploadAttachmentAlarmIdList": [1,2],
    "attachmentRetention": 30
  }
}'
```
