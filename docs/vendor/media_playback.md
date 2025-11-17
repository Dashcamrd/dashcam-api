# Endpoint Spec: Playback

- Endpoint name (internal): media_playback
- Vendor URL path: /api/v1/media/playback
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - channels: array<int> (required)
  - dataType: int (required) — 0 or 1 per docs
  - streamType: int (required) — 0 main, 1 sub
  - method: int (required) — 0 normal, 1 FF, 2 keyframe rewind, 3 keyframe, 4 single frame
  - multiple: int (required) — speed (0 invalid, 1=1x, 2=2x, 3=4x, 4=8x, 5=16x)
  - startTime: int seconds (required)
  - endTime: int seconds (required)
- Response success condition: code == 200
- Response data path: data.videos[] with fields deviceId, channel, playUrl, errCode, errDesc

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/media/playback' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "10620010051",
  "channels": [2],
  "dataType": 0,
  "streamType": 0,
  "method": 0,
  "multiple": 0,
  "startTime": 1715568599,
  "endTime": 1715568757
}'
```
