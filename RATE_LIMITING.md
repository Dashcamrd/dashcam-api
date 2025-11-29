# Rate Limiting & Retry Logic

## Overview

The manufacturer API service now includes:
- ✅ **Per-endpoint timeouts** - Configurable timeouts per endpoint
- ✅ **Automatic retries** - Exponential backoff retry logic
- ✅ **Rate limiting** - Configurable requests per minute limit
- ✅ **Connection error handling** - Automatic retry on connection failures

## Configuration

### Global Settings (in `config/manufacturer_api.yaml`)

```yaml
profiles:
  default:
    default_timeout: 30        # Default timeout in seconds
    default_retries: 3         # Default number of retry attempts
    default_retry_delay: 1     # Initial retry delay (seconds, exponential backoff)
    rate_limit_per_minute: 60 # Max requests per minute (0 = disabled)
```

### Per-Endpoint Settings

Override defaults for specific endpoints:

```yaml
gps_search_v1:
  path: /api/v1/gps/search
  method: POST
  timeout: 60      # Override: GPS searches take longer
  retries: 2       # Override: Fewer retries for time-consuming ops
  request:
    required: [deviceId, startTime, endTime]
```

## Features

### 1. Per-Endpoint Timeouts

Each endpoint can have its own timeout:

```python
# In config/manufacturer_api.yaml
gps_search_v1:
  timeout: 60  # 60 seconds for GPS searches
```

If not specified, uses `default_timeout` (30s).

### 2. Automatic Retries with Exponential Backoff

**Retry Logic:**
- Automatically retries on:
  - `requests.exceptions.Timeout` - Request timeout
  - `requests.exceptions.ConnectionError` - Network/connection errors
  - Other `requests.exceptions.RequestException` - General request errors

**Backoff Strategy:**
- Initial delay: `retry_delay` seconds (default: 1s)
- Exponential backoff: `delay = retry_delay * (2 ** retry_count)`
- Example: 1s → 2s → 4s → 8s

**Logging:**
```
⏱️  [a3f2c1d4] Request timeout after 30s
🔄 [a3f2c1d4] Retrying in 1s... (attempt 2/4)
🔄 [a3f2c1d4] Retrying in 2s... (attempt 3/4)
```

### 3. Rate Limiting

**Sliding Window Rate Limiter:**
- Tracks requests in a 60-second window
- Automatically waits when limit is reached
- Logs rate limit events

**Configuration:**
```yaml
rate_limit_per_minute: 60  # Max 60 requests per minute
```

**Behavior:**
- If limit reached, waits until oldest request expires
- Then proceeds with new request
- Logs: `⏳ Rate limit reached (60/min), waiting 2.3s...`

**Disable Rate Limiting:**
```yaml
rate_limit_per_minute: 0  # Disables rate limiting
```

### 4. Connection Error Handling

Automatically handles:
- Network timeouts
- Connection refused
- DNS failures
- Server errors

All retried with exponential backoff.

## Usage Examples

### Default Timeout (30s, 3 retries)

```python
# Uses default_timeout: 30s, default_retries: 3
result = manufacturer_api.get_user_device_list({"page": 1, "pageSize": 10})
```

### Custom Timeout Per Endpoint

```yaml
# In config/manufacturer_api.yaml
gps_query_detailed_track_v1:
  timeout: 90      # 90 seconds for detailed track queries
  retries: 2       # Only 2 retries (queries are slow)
```

### Rate Limiting in Action

```
# First 60 requests: ✅ Immediate
# 61st request: ⏳ Rate limit reached, waiting...
# After wait: ✅ Proceeds
```

## Monitoring

### Correlation IDs

All retries include correlation IDs for tracing:

```python
# Log output:
📡 [a3f2c1d4] Making POST request to /api/v1/gps/search (timeout: 60s)
⏱️  [a3f2c1d4] Request timeout after 60s
🔄 [a3f2c1d4] Retrying in 1s... (attempt 2/3)
📡 [a3f2c1d4] Making POST request to /api/v1/gps/search (timeout: 60s) (attempt 2/3)
```

### Log Patterns

**Find retries:**
```bash
grep "Retrying" server.log
```

**Find rate limits:**
```bash
grep "Rate limit reached" server.log
```

**Find timeouts:**
```bash
grep "Request timeout" server.log
```

## Configuration Best Practices

### Timeouts

- **Fast endpoints** (device list, states): `timeout: 15`
- **Medium endpoints** (GPS latest): `timeout: 30` (default)
- **Slow endpoints** (GPS search, track history): `timeout: 60-90`
- **Very slow** (detailed track, large date ranges): `timeout: 120`

### Retries

- **Quick operations**: `retries: 3` (default)
- **Time-consuming**: `retries: 2` (fewer retries to avoid long waits)
- **Critical operations**: `retries: 5` (more retries for important calls)

### Rate Limits

- **Conservative**: `rate_limit_per_minute: 30`
- **Normal**: `rate_limit_per_minute: 60` (default)
- **Aggressive**: `rate_limit_per_minute: 120`
- **No limit**: `rate_limit_per_minute: 0`

## Performance Impact

### Retry Overhead

- **First attempt**: Normal latency
- **With retries**: Adds exponential backoff delays
- **Example**: 3 retries with 1s delay = max +7s (1s + 2s + 4s)

### Rate Limiting Overhead

- **Within limit**: No overhead
- **At limit**: Waits for window to clear (typically < 1s)
- **Logging**: Minimal overhead from timestamp tracking

## Testing

To test retry logic:

```bash
# Temporarily lower timeout to force retries
# Edit config/manufacturer_api.yaml:
gps_search_v1:
  timeout: 1  # Very short timeout
  retries: 3
```

To test rate limiting:

```bash
# Lower rate limit temporarily
rate_limit_per_minute: 5  # Easy to hit
# Then make multiple rapid requests
```

## Status

✅ **Implemented and tested:**
- Per-endpoint timeouts
- Exponential backoff retries
- Rate limiting with sliding window
- Connection error handling
- Correlation ID tracking

🎯 **Current Configuration:**
- Default timeout: 30s
- Default retries: 3
- Rate limit: 60/min
- GPS search timeout: 60s, 2 retries

## Future Enhancements

Potential improvements:
- Per-endpoint rate limits
- Circuit breaker pattern
- Request queuing
- Adaptive timeouts based on response times
- Metrics collection for retry/rate limit events

