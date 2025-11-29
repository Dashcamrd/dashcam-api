# Endpoint Spec: Get Device Resource Calendar

- Endpoint name (internal): media_get_video_calendar
- Vendor URL path: /api/v1/media/getVideoCalendar
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - mediaType: uint32 (required) — 0 all, 1 audio, 2 video
  - year: uint32 (required)
  - month: uint32 (required, 1-12)
- Response success condition: code == 200
- Response data path: data.days[] (bool[32], index 1..31 = day present)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/media/getVideoCalendar' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "17513507093",
  "mediaType": 0,
  "year": 2024,
  "month": 5
}'
```
