# Endpoint Spec: Query Device Resource List

- Endpoint name (internal): media_get_file_list
- Vendor URL path: /api/v1/media/getFileList
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema (all optional unless noted):
  - deviceId: string (required)
  - channel: uint32 (optional, 0=all)
  - startTime: uint32 seconds (optional, 0=no lower bound)
  - endTime: uint32 seconds (optional, 0=no upper bound)
  - alarmFlags: object (optional) — see GPSInfoV2 Alarm Flags
  - videoAlarmFlags: object (optional) — see table below
  - mediaType: uint32 (optional) — 0 AV, 1 Audio, 2 Video, 3 Video or AV
  - streamType: uint32 (optional) — 0 all, 1 main, 2 sub
  - storageType: uint32 (optional) — 0 all, 1 primary, 2 DR
- Response success condition: code == 200
- Response data path: data.mediaList[] and data.total
- Key fields:
  - mediaList[].channel, startTime (s), endTime (s), mediaType, streamType, storageType, fileSize

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/media/getFileList' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "deviceId": "17513507093",
  "channel": 1,
  "startTime": 1714003200,
  "endTime": 1714262400,
  "mediaType": 0,
  "streamType": 1,
  "storageType": 1
}'
```
