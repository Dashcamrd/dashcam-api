# Endpoint Spec: GPS Fuzzy Query V2 (Track Dates)

- Endpoint name (internal): gps_fuzzy_query_v2
- Vendor URL path: /api/v2/gps/fuzzyQuery
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - startTime: int64 seconds (required)
  - endTime: int64 seconds (required)
  - Note: interval must not exceed 31 days
- Response success condition: code == 200
- Response data path: data.deviceId, data.days[] (YYYY-MM-DD)
- Field mapping: days[] -> available dates list

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v2/gps/fuzzyQuery' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "18109526951",
  "startTime": 1726934400,
  "endTime": 1729612800
}'
```
