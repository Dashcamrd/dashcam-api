# Vendor Endpoint Specification Template

Fill one of these for each endpoint before we flip adapters. No guessing.

- Endpoint name (internal):
- Vendor URL path:
- HTTP method:
- Required headers:
- Auth details (token type, header name):
- Query params:
- Request body schema (fields, types, required, defaults, units):
- Response success condition (code/value):
- Response data path to payload (e.g., `data.gpsInfo`):
- Field mapping to DTOs (name, type, units):
- Pagination (if any):
- Error codes and meanings:
- Sample success response (redacted):
- Sample error response (redacted):

## Example (GPS Latest)
- Endpoint name: gps_search_latest
- Vendor URL path: /api/v1/gps/search
- Method: POST
- Headers: X-Token
- Request:
  - deviceId: string (required)
  - startTime: int seconds (required)
  - endTime: int seconds (required)
- Response success: code == 200
- Data path: data.gpsInfo[0]
- Map:
  - latitude (int 1e6) -> dto.latitude (float degrees)
  - longitude (int 1e6) -> dto.longitude (float degrees)
  - time (sec|ms) -> dto.timestamp_ms (ms)
  - speed -> dto.speed_kmh
  - direction -> dto.direction_deg
