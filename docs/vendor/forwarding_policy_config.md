# Spec: Forwarding Policy Configuration

- Root: PolicyConfig
- Structure:
```json
{
  "msgIds": [1,2,3],
  "gps": {"coordinateType": 1, "parseAdditionalInfo": true},
  "alarm": {"alarmTypes": [1,2,8], "forwardingType": 2, "coordinateType": 1}
}
```

Fields
- msgIds: required, unique; 1=GPS, 2=Alarm, 3=DeviceStatus, 4=DataForwarding, 5=DriverIdentity
- gps (when 1 included):
  - coordinateType: 1 WGS84, 2 GCJ02, 3 BD09
  - parseAdditionalInfo: bool, default false
- alarm (when 2 included):
  - alarmTypes: array of int (see Alarm Type Description)
  - forwardingType: 1 ALL, 2 SUDDEN
  - coordinateType: same enum as gps

Validation
- msgIds non-empty; if includes 1 then gps required; if includes 2 then alarm required
- Enumerations must be valid; no duplicates

Common combinations
- [1]: GPS only
- [2]: Alarm only
- [1,2,3]: GPS + Alarm + Status

Examples
- GPS basic: coordinateType=1, parseAdditionalInfo=false
- Alarm sudden: alarmTypes [1,2,8], forwardingType=2
