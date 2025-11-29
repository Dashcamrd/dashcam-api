# Endpoint Spec: GPS Get Latest GPS V2

- Endpoint name (internal): gps_get_latest_v2
- Vendor URL path: /api/v2/gps/getLatestGPS
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceIds: array<string> (required) — up to 100 per request
- Response success condition: code == 200
- Response data path: data.list[] with fields deviceId, gps (GPSInfoV2), lastOnlineTime (s)
- Field mapping to DTOs:
  - list[].gps.latitude/longitude -> LatestGpsDto.latitude/longitude
  - list[].gps.speed (1/10 km/h) -> speed_kmh /10
  - list[].gps.time (s) -> timestamp_ms *1000
  - list[].gps.altitude -> altitude_m
  - list[].lastOnlineTime (s) -> AccStateDto.last_online_time_ms *1000

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v2/gps/getLatestGPS' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceIds": ["18109526951", "18109526952", "18109526953"]
}'
```

## Sample Success Response (from docs)
```json
{
  "code": 200,
  "message": "success",
  "data": {"list": [ {"deviceId": "18109526951", "gps": {"latitude": 22.649954, "longitude": 114.148194, "speed": 359, "direction": 240, "time": 1726934400, "altitude": 73}, "lastOnlineTime": 1726934500} ]},
  "ts": 1726934600
}
```
