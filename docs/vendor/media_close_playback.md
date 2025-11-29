# Endpoint Spec: Close Playback

- Endpoint name (internal): media_close_playback
- Vendor URL path: /api/v1/media/playbackControl
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - channels: array<int> (required)
  - controlType: int (required) — fixed value 2
- Response success condition: code == 200
- Response data path: data (empty object)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/media/playbackControl' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "10620010051",
  "channels": [1],
  "controlType": 2
}'
```

## Sample Success Response (from docs)
```json
{ "code": 200, "message": "success", "ts": 1716263339, "data": {} }
```
