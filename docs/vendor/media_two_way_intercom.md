# Endpoint Spec: Two-Way Intercom

- Endpoint name (internal): media_two_way_intercom
- Vendor URL path: /api/v1/media/deviceTwoWayVoip
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - channel: int32 (required)
- Response success condition: code == 200 and data.errorCode == 200
- Response data path: data { deviceId, playUrl, pushUrl, errorDesc, errorCode }

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/media/deviceTwoWayVoip' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "device001",
  "channel": 1
}'
```

## Sample Success Response (from docs)
```json
{
  "code": 200,
  "message": "success",
  "ts": 1735881834,
  "data": {
    "deviceId": "12345678999",
    "playUrl": "https://116.247.83.154:9359/index/api/webrtc?app=live&stream=012345678999_1_voip&type=play",
    "pushUrl": "https://116.247.83.154:9359/index/api/webrtc?app=live&stream=012345678999_1&type=push",
    "errorDesc": "",
    "errorCode": 200
  }
}
```
