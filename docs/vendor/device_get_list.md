# Endpoint Spec: Get User Device List

- Endpoint name (internal): device_get_list
- Vendor URL path: /api/v1/device/getList
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required) — token from Login
- Auth details: token required in header `X-Token`
- Query params: none
- Request body schema:
  - companyId: int64 (optional) — filter company and subs if omitted uses current
  - deviceIds: array<string> (optional) — up to 1000
  - plateNumbers: array<string> (optional) — up to 1000
  - sns: array<string> (optional) — up to 1000
  - page: int64 (required) — starts at 1, default 1
  - pageSize: int64 (required) — default 10, max 1000
- Response success condition: code == 200
- Response data path: data.list (array), data.total (int)
- Field mapping to DTOs (subset):
  - list[].deviceId -> DeviceDto.device_id
  - list[].plateNumber -> DeviceDto.plate_no
  - list[].state -> DeviceDto.online (0 offline, 1 online, 2 low power)
  - list[].accState -> DeviceDto.acc_on (0/1)
  - list[].expirationTime -> seconds (convert to ms if needed)
- Pagination: page/pageSize, total in response
- Error codes and meanings: Not specified in HTML (confirm with vendor docs)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/device/getList' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
    "companyId": 513,
    "deviceIds": ["12345", "123456"],
    "page": 1,
    "pageSize": 10
}'
```

## Sample Success Response (from docs)
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "deviceId": "12345",
        "plateNumber": "TEST",
        "companyId": 513,
        "companyName": "Test",
        "fleetId": 5073,
        "fleetName": "MA9504E-B1",
        "maxChannel": 12,
        "protoType": 0,
        "expirationTime": 1740412800,
        "sn": "SN12345",
        "isAutoUpdate": true,
        "state": 1,
        "accState": 1,
        "createdAt": 1700000000,
        "updatedAt": 1710000000
      },
      {
        "deviceId": "123456",
        "plateNumber": "TEST",
        "companyId": 513,
        "companyName": "Test",
        "fleetId": 9353,
        "fleetName": "MA9704E-B1-V2",
        "maxChannel": 12,
        "protoType": 1,
        "expirationTime": 0,
        "sn": "SN123456",
        "isAutoUpdate": false,
        "state": 0,
        "accState": 0,
        "createdAt": 1700000000,
        "updatedAt": 1710000000
      }
    ],
    "total": 2
  },
  "ts": 1715321710
}
```
