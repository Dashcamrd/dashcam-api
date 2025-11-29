# Endpoint Spec: Get Organization Tree

- Endpoint name (internal): org_get_tree
- Vendor URL path: /api/v1/organization/getTree
- HTTP method: POST
- Required headers:
  - Content-Type: application/json
  - X-Token: string (required) — token from Login
- Auth details: token required in header `X-Token`
- Query params: none
- Request body schema:
  - parentId: int64 (required) — Parent Company ID
  - type: int64 (required) — Fixed value 1 (Company)
- Response success condition: code == 200
- Response data path: data (object representing org node with children array)
- Field mapping to DTOs: N/A (structure consumed directly if needed)
- Pagination: none
- Error codes and meanings: Not specified in HTML (confirm with vendor docs)

## Sample Request (from docs, URL corrected)
```bash
curl --location --request POST 'http://180.167.106.70:9337/api/v1/organization/getTree' \
--header 'Content-Type: application/json' \
--header 'X-Token: <JWT_TOKEN>' \
--data '{
    "parentId": 1,
    "type": 1
}'
```

## Sample Success Response (from docs)
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1001,
    "name": "Headquarters",
    "parentId": 0,
    "type": 1,
    "deviceNumber": 120,
    "authorizedNumber": 200,
    "userId": 101,
    "username": "admin",
    "roleId": 1,
    "roleName": "Administrator",
    "children": [
      {
        "id": 1002,
        "name": "Branch 1",
        "parentId": 1001,
        "type": 1,
        "deviceNumber": 50,
        "authorizedNumber": 80,
        "userId": 102,
        "username": "manager1",
        "roleId": 2,
        "roleName": "Branch Manager",
        "children": []
      },
      {
        "id": 1003,
        "name": "Branch 2",
        "parentId": 1001,
        "type": 1,
        "deviceNumber": 40,
        "authorizedNumber": 60,
        "userId": 103,
        "username": "manager2",
        "roleId": 2,
        "roleName": "Branch Manager",
        "children": []
      }
    ]
  },
  "ts": 1714016117
}
```
