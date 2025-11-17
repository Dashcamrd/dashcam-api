# Spec: Forwarding Message Specification

- Message root: ForwardingMessage
- Discriminator: msgId (1=GPS, 2=Alarm, 3=DeviceStatus, 4=DataForwarding, 5=DriverIdentity)
- Only the field matching msgId is present in one message

## 1) GPS (msgId=1)
- Field: gps.list[] (GPSInfoV2/T808_0x0200)
- Core fields per item: deviceId, latitude, longitude, speed(1/10 km/h), direction, time(s), altitude(m), alarmFlags, statusFlags, additionalInfos[], dataType(0=realtime,1=retransmit)
- Batch allowed: 1..200 entries

Example
```json
{
  "msgId": 1,
  "gps": {"list": [{"deviceId": "device001", "latitude": 39.908823, "longitude": 116.39747, "speed": 60.5, "direction": 180, "time": 1735888579, "altitude": 50.2, "additionalInfos": [], "dataType": 0}]}
}
```

## 2) Alarm (msgId=2)
- Field: alarm.base + alarm.list[]
- base: snapshot of location/status at alarm (deviceId, flags, lat/lng, speed, dir, time, altitude, dataType)
- list[]: items with type, status(0/1/2) and one content object (adas|dsm|bsd|sda|geofenceOverSpeed|geofenceInOut|geofenceRouteTime|sensorTemperature|sensorTirePressure|sensorOil|extensionIO|storageFault)

## 3) Device Status (msgId=3)
- Field: deviceStatusNotification { deviceId, state(0=offline,1=online), timestamp(s) }

## 4) Data Forwarding (msgId=4)
- Field: dataForwarding { deviceId, type(uint32), content(base64 bytes), timestamp(s) }
- type examples: 0(GNSS detail), 11(IC card), 65/66(serial ports), 240-255(user-defined)

## 5) Driver Identity (msgId=5)
- Field: driverIdentityInformationReporting { deviceId, status(1 insert/2 remove), timestamp(s), icCardReadResult, qualificationCode, issuingAuthority, certificateValidity, driverIDCardNumber, driverName }

Notes
- Coordinates may be WGS84/GCJ02/BD09 based on policy; do not re-convert.
- All timestamps are seconds.
- additionalInfos include mileage/fuel/signal/satellites etc.
