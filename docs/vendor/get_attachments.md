# Endpoint Spec: Get Attachments

- Endpoint name (internal): stat_get_attachments
- Vendor URL path: /api/v1/stat/common/getAttachment
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required)
- Request body schema:
  - path: string (required) — attachment path (e.g., "13800138000/file1.jpg")
- Response success condition: code == 200
- Response data path: data.file (base64-encoded)

## Sample Request (URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/stat/common/getAttachment' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
  "path": "13800138000/file1.jpg"
}'
```

## Sample Success Response (from docs)
```json
{
  "code": 200,
  "message": "success",
  "data": { "file": "<base64>" },
  "ts": 1732845227
}
```
