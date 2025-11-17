# Endpoint Spec: Preview and Monitor

- Endpoint name (internal): media_preview
- Vendor URL path: /api/v1/media/previewVideo
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - channels: array<int> (required)
  - dataType: int (required) — 1:Preview, 3:Monitor
  - streamType: int (required) — 0 main, 1 sub
- Response success condition: code == 200
- Response data path: data.videos[] with fields deviceId, channel, playUrl

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/media/previewVideo' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "17721038890",
  "channels": [1],
  "dataType": 1,
  "streamType": 0
}'
```
