#!/bin/bash

# Get your server URL from environment or use default
BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "========================================="
echo "TESTING STREAM FORMAT FROM YOUR API"
echo "========================================="
echo ""

# First, login to get token
echo "1. Getting access token..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123",
    "device_id": "1827076113"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✓ Got token: ${TOKEN:0:20}..."
echo ""

# Get preview stream
echo "2. Requesting video preview..."
echo "   Testing MAIN STREAM (high quality)..."
PREVIEW_RESPONSE=$(curl -s -X POST "${BASE_URL}/media/preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "device_id": "1827076113",
    "channel": 1,
    "stream": 1
  }')

echo ""
echo "Preview Response:"
echo "$PREVIEW_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PREVIEW_RESPONSE"
echo ""

# Extract and analyze playUrl
PLAY_URL=$(echo $PREVIEW_RESPONSE | grep -o '"play_url":"[^"]*' | cut -d'"' -f4 | head -1)

if [ -n "$PLAY_URL" ]; then
  echo "========================================="
  echo "STREAM URL ANALYSIS"
  echo "========================================="
  echo "Full URL: $PLAY_URL"
  echo ""
  
  # Detect protocol
  if echo "$PLAY_URL" | grep -q "^ws://"; then
    echo "Protocol: WebSocket (ws://)"
    echo "Format: ❌ NOT COMPATIBLE with iOS AVPlayer"
    echo "Recommendation: Use WebView (current solution) or media_kit"
  elif echo "$PLAY_URL" | grep -q "^wss://"; then
    echo "Protocol: Secure WebSocket (wss://)"
    echo "Format: ❌ NOT COMPATIBLE with iOS AVPlayer"
    echo "Recommendation: Use WebView (current solution) or media_kit"
  elif echo "$PLAY_URL" | grep -q "^rtsp://"; then
    echo "Protocol: RTSP"
    echo "Format: ❌ NOT COMPATIBLE with web browsers or iOS video_player"
    echo "Recommendation: Use media_kit or VLC player"
  elif echo "$PLAY_URL" | grep -q "^rtmp://"; then
    echo "Protocol: RTMP"
    echo "Format: ❌ NOT COMPATIBLE with web browsers or iOS video_player"
    echo "Recommendation: Use media_kit or VLC player"
  elif echo "$PLAY_URL" | grep -q ".m3u8"; then
    echo "Protocol: HLS (HTTP Live Streaming)"
    echo "Format: ✅ PERFECT for iOS! Native support"
    echo "Recommendation: Switch to native video_player package!"
  elif echo "$PLAY_URL" | grep -q "^http" && echo "$PLAY_URL" | grep -q ".mp4"; then
    echo "Protocol: HTTP Progressive Download (MP4)"
    echo "Format: ✅ GOOD for iOS! Native support"
    echo "Recommendation: Switch to native video_player package!"
  elif echo "$PLAY_URL" | grep -q "^http.*\.flv"; then
    echo "Protocol: HTTP-FLV"
    echo "Format: ❌ NOT COMPATIBLE with iOS AVPlayer"
    echo "Recommendation: Keep WebView or use media_kit"
  elif echo "$PLAY_URL" | grep -q "^http"; then
    echo "Protocol: HTTP (unknown subtype)"
    echo "Format: ⚠️ MAYBE COMPATIBLE - needs testing"
    echo "Recommendation: Test with native video_player first"
  else
    echo "Protocol: Unknown"
    echo "Format: ❓ Cannot determine compatibility"
  fi
  echo ""
else
  echo "❌ Could not extract play_url from response"
fi

# Close preview
echo "3. Closing preview session..."
curl -s -X POST "${BASE_URL}/media/preview/close?device_id=1827076113" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
echo "✓ Done"
echo ""
