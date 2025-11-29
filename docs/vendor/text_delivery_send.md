# Endpoint Spec: Text Delivery (single device, real-time)

- Endpoint name (internal): text_delivery_send
- Vendor URL path: /api/v1/textDelivery/send
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - name: string (required)
  - content: string (required)
  - contentTypes: array<string> (required) — ["1" (screen), "2" (voice)]
  - deviceId: string (required)
  - ignoreLowPower: uint32 (optional) — 0 wait online, 1 deliver in low power
- Response success condition: code == 200
- Response data path: data (empty)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/textDelivery/send' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "name": "test",
  "content": "1231",
  "contentTypes": ["1", "2"],
  "deviceId": "17721028810",
  "operator": "admin"
}'
```
