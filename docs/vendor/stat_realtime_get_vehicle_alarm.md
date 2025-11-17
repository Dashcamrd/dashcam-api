# Endpoint Spec: Query Vehicle Alarms in Last 3 Hours

- Endpoint name (internal): stat_realtime_get_vehicle_alarm
- Vendor URL path: /api/v1/stat/realtime/getVehicleAlarm
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - start: int64 seconds (required)
  - end: int64 seconds (required)
  - pageArg: object (required)
    - page: uint32 (required)
    - pageSize: uint32 (required)
- Response success condition: code == 200
- Response data path: data.vehicles[], data.pageArg
- Notable fields: vehicles[].deviceId, plateNumber, companyName, fleetName, alarm{typeId, level, id, flag, speed, altitude, latitude, longitude, happenAt, ...}, alarmSign{...}, vehicleState{...}

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/stat/realtime/getVehicleAlarm' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "13800138000",
  "start": 1703664000,
  "end": 1703667600,
  "pageArg": { "page": 1, "pageSize": 10 }
}'
```
