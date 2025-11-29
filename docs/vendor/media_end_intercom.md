# Endpoint Spec: End Intercom

- Endpoint name (internal): media_end_intercom
- Vendor URL path: /api/v1/media/closeDeviceTwoWayVoip
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - deviceId: string (required)
  - channel: int32 (required)
- Response success condition: code == 200
- Response data path: data (empty)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/media/closeDeviceTwoWayVoip' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "device001",
  "channel": 1
}'
```

## Sample Success Response (from docs)
```json
{ "code": 200, "message": "success", "ts": 1714016117 }
```
