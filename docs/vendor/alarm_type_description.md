# Reference: Alarm Type Description

- Purpose: Enumerates alarm type codes (typeId) and categories used across statistics APIs.
- Encoding: 6-digit AABBCC
  - AA: primary category (e.g., 11 common, 12 channel, 13 geofence, 64 ADAS, 65 DSM, 66 BSD, 70 SDA)
- Usage:
  - Request fields: typeId (single), typeIdList (multiple)
  - Present in: stat_realtime_get_vehicle_alarm, stat_history_get_vehicle_statistic, stat_history_get_vehicle_detail

## Example Ranges
- ADAS: 640001-640101
- BSD: 660001-660003
- DSM: 650001-651512
- SDA: 700001-700007
- Common: 110100-110305
- Channel: 120101-120102
- Geofence: 130101-130102

Consult vendor HTML for the full table when mapping UI filters.
