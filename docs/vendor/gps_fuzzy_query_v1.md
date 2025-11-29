# Endpoint Spec: GPS Query Track Dates (v1)

- Endpoint name (internal): gps_fuzzy_query_v1
- Vendor URL path: /api/v1/gps/fuzzyQuery
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - startTime: int64 seconds (required)
  - endTime: int64 seconds (required)
- Response success condition: code == 200
- Response data path: data.deviceId, data.days[] (YYYY-MM-DD)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/gps/fuzzyQuery' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "02207000128",
  "startTime": 1713139200,
  "endTime": 1713571200
}'
```
