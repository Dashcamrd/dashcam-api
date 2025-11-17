# Spec: Forwarding Platform Configuration

- Root: PlatformConfig
- Current support: HTTP JSON (protocol=1)

Structure
```json
{
  "protocol": 1,
  "httpConfig": {
    "url": "https://api.example.com/data",
    "headers": {"Authorization": "Bearer ...", "Content-Type": "application/json"},
    "timeout": 30
  }
}
```

Fields
- protocol: 1 HTTP
- httpConfig.url: required, valid http/https URL
- httpConfig.headers: optional map<string,string>
- httpConfig.timeout: optional seconds (default 30, 5-60 recommended)

Status
- PLATFORM_STATUS_DISABLED=0, PLATFORM_STATUS_ENABLED=1

Best practices
- Prefer HTTPS; include Content-Type; set reasonable timeouts; use standard headers.
