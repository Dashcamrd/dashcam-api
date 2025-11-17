# Endpoint Spec: GPS Query Detailed Track (v1)

- Endpoint name (internal): gps_search_v1
- Vendor URL path: /api/v1/gps/search
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - startTime: int64 seconds (required)
  - endTime: int64 seconds (required)
- Response success condition: code == 200
- Response data path: data.gpsInfo[]
- Field mapping to DTOs:
  - gpsInfo[].latitude/longitude (int scaled 1e6) -> divide by 1_000_000.0
  - gpsInfo[].time (string "YYYY-MM-DD HH:mm:ss" or seconds) -> parse to ms
  - gpsInfo[].speed -> speed_kmh (units not specified; confirm)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/gps/search' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "device001",
  "startTime": 1704067200,
  "endTime": 1704153600
}'
```
