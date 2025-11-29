# Endpoint Spec: Close Preview

- Endpoint name (internal): media_close_preview
- Vendor URL path: /api/v1/media/closePreviewVideo
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - channels: array<int> (required)
  - dataType: int (required) — 1
  - streamType: int (required) — 0 main, 1 sub
- Response success condition: code == 200
- Response data path: data (empty)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/media/closePreviewVideo' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "17721038890",
  "channels": [1],
  "dataType": 1,
  "streamType": 0
}'
```

## Sample Success Response (from docs)
```json
{ "code": 200, "message": "success", "data": {}, "ts": 1714361263 }
```
