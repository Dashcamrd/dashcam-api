# Endpoint Spec: GPS Search V2 (Detailed Track)

- Endpoint name (internal): gps_search_v2
- Vendor URL path: /api/v2/gps/search
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - startTime: int64 seconds (required)
  - endTime: int64 seconds (required)
  - Note: time interval must not exceed 3 days
- Response success condition: code == 200
- Response data path: data.list[] (GPSInfoV2)
- Field mapping to DTOs:
  - list[].latitude/longitude -> TrackPointDto latitude/longitude
  - list[].speed (1/10 km/h) -> speed_kmh /10
  - list[].time (s) -> timestamp_ms *1000
  - list[].direction -> direction_deg

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v2/gps/search' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "18109526951",
  "startTime": 1726934400,
  "endTime": 1727020800
}'
```
