# Endpoint Spec: Statistics By Vehicle

- Endpoint name (internal): stat_history_get_vehicle_statistic
- Vendor URL path: /api/v1/stat/history/getVehicleStatistic
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - start: int64 seconds (required)
  - end: int64 seconds (required)
  - deviceIdList: array<string> (required)
  - typeIdList: array<uint32> (required)
  - timestamp: int64 (optional)
  - pageArg: object (required)
    - page: uint32 (required)
    - pageSize: uint32 (required)
- Response success condition: code == 200
- Response data path: data.vehicles[], data.timestamp, data.pageArg
- Notable fields: vehicles[].total, statEntryList[{typeId, number, statAttachment{...}}]

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/stat/history/getVehicleStatistic' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "start": 1703664000,
  "end": 1703667600,
  "deviceIdList": ["13800138000", "13800138001"],
  "typeIdList": [640002, 640003, 640004],
  "timestamp": 1703664000,
  "pageArg": { "page": 1, "pageSize": 10 }
}'
```
