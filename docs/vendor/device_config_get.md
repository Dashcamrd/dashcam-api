# Endpoint Spec: Get Device Configuration

- Endpoint name (internal): device_config_get
- Vendor URL path: /api/v1/device/config/get
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required) — token from Login
- Auth details: token required in header `X-Token`
- Query params: none
- Request body schema:
  - deviceId: string (required) — Terminal device ID
  - command: string (required) — Query command, e.g. "$SYSTEMINFO"
- Response success condition: code == 200
- Response data path: data.config (string)
- Field mapping to DTOs: N/A (raw config string)
- Pagination: none
- Error codes and meanings: Not specified in HTML (confirm with vendor docs)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/device/config/get' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
    "deviceId": "10620010051",
    "command": "$SYSTEMINFO"
}'
```

## Sample Success Response (from docs)
```json
{
  "code": 200,
  "message": "success",
  "ts": 1735885534,
  "data": {
    "config": "$SYSTEMINFO,1*MA9504E-WP,2*CM017318270240478,3*M-R100,4*STD-S101V012(10200-204-209-211),5*MCU-V110,6*0001-00-007E-0001,7*Quectel,8*EC200UCNLA,9*EC200UCNLAR02A09M08,10*867192067562683,11*,12*1.00 (59842),13*AI,14*V1.0,15*R05P016,16*0000001,17*,18*,19*ADAS-DSM-BSD1-BSD2-BSD3,20*BSD1,21*BSD1;"
  }
}
```
