# Spec: Data Forwarding Specification

Overview
- Defines overall data forwarding architecture, flow, and configuration steps
- Uses Forwarding Platform + Forwarding Policy → emits ForwardingMessage per policy

Flow (high level)
- Device → GPS Service → Data Receiver → Policy Engine → Protocol Converter → Forwarder → Third-party Platform
- Logs recorded; caching and queues involved

Configure (steps)
1) Create Forwarding Platform (protocol=http, url, headers, timeout)
2) Create Forwarding Policy (scope by company or by device)
   - configType: 1 by company (forwardCompanyId), 2 by device (deviceIds)
   - configs.msgIds, gps, alarm

Message types
- See forwarding_message_spec.md

Notes
- All timestamps in seconds
- Coordinate system controlled by policy; avoid repeated conversions
- Configuration changes refresh cache within minutes
