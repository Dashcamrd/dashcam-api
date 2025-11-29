# Endpoint Spec: Get Device Status List

- Endpoint name (internal): device_states
- Vendor URL path: /api/v1/device/states
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required) — token from Login
- Auth details: token required in header `X-Token`
- Query params: none
- Request body schema:
  - deviceIds: array<string> (required) — Array of device IDs, e.g. ["10620010051"]
- Response success condition: code == 200
- Response data path: data.list (array)
- Field mapping to DTOs:
  - list[].deviceId -> DeviceDto.device_id
  - list[].state -> online (0=offline, 1=online, 2=low power)
  - list[].accState -> AccStateDto.acc_on (0/1)
- Pagination: none
- Error codes and meanings: Not specified in HTML (confirm with vendor docs)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/device/states' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
    "deviceIds": ["10620010051"]
}'
```

## Sample Success Response (from docs)
```json
{
  "code": 200,
  "message": "success",
  "ts": 1735885534,
  "data": {
    "list": [
      { "deviceId": "10620010051", "state": 1, "accState": 1 }
    ]
  }
}
```
