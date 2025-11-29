# Spec: GPSInfoV2 (T808_0x0200)

Basic fields (from docs):
- deviceId: string
- alarmFlags: object (see Alarm Flags)
- statusFlags: object (see Status Flags)
- latitude: float64 (WGS84)
- longitude: float64 (WGS84)
- speed: float64 (unit: 1/10 km/h)
- direction: int64 (0–359)
- time: int64 (timestamp seconds)
- altitude: float64 (meters)
- additionalInfos: array (see Additional Info types)
- dataType: int64 (0 real-time, 1 retransmission)

Useful mappings to DTOs:
- latitude, longitude -> LatestGpsDto.latitude/longitude (no scaling needed)
- speed (1/10 km/h) -> speed_kmh = speed / 10.0
- time (s) -> timestamp_ms = time * 1000
- altitude -> altitude_m
- statusFlags.acc -> AccStateDto.acc_on

See tables in vendor HTML for Alarm/Status/Additional info details.
