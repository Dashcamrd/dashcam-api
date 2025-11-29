# Endpoint Spec: Query Vehicle Details

- Endpoint name (internal): stat_history_get_vehicle_detail
- Vendor URL path: /api/v1/stat/history/getVehicleDetail
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - start: int64 seconds (required)
  - end: int64 seconds (required)
  - deviceId: string (required)
  - typeId: uint32 (required) — alarm type code (see Alarm Type Description)
  - timestamp: int64 (optional) — cache query timestamp
  - pageArg: object (required)
    - page: uint32 (required)
    - pageSize: uint32 (required)
- Response success condition: code == 200
- Response data path: data.vehicles[], data.timestamp, data.pageArg

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/stat/history/getVehicleDetail' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "start": 1703664000,
  "end": 1703667600,
  "deviceId": "13800138000",
  "typeId": 640002,
  "timestamp": 1703664000,
  "pageArg": { "page": 1, "pageSize": 10 }
}'
```
