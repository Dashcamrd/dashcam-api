#!/bin/bash

echo "=========================================="
echo "TESTING IF PREVIEW ENDPOINT SUPPORTS WebRTC"
echo "=========================================="
echo ""

# Check if backend is running locally
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    BASE_URL="http://localhost:8000"
    echo "✓ Using local backend: $BASE_URL"
elif curl -s https://dashcam-api.onrender.com/docs > /dev/null 2>&1; then
    BASE_URL="https://dashcam-api.onrender.com"
    echo "✓ Using Render backend: $BASE_URL"
else
    echo "❌ Backend not found. Please provide the URL:"
    read -p "Backend URL: " BASE_URL
fi

echo ""
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_no": "2005",
    "password": "fam123456789"
  }')

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to login"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✓ Logged in successfully"
echo ""

# Test different stream types
for STREAM_TYPE in 1 2; do
  echo "=========================================="
  if [ $STREAM_TYPE -eq 1 ]; then
    echo "Testing MAIN STREAM (High Quality)"
  else
    echo "Testing SUB STREAM (Low Latency)"
  fi
  echo "=========================================="
  echo ""
  
  PREVIEW_RESPONSE=$(curl -s -X POST "${BASE_URL}/media/preview" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{
      \"device_id\": \"18270761136\",
      \"channel\": 1,
      \"stream\": $STREAM_TYPE
    }")
  
  echo "Response:"
  echo "$PREVIEW_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PREVIEW_RESPONSE"
  echo ""
  
  # Extract play_url
  PLAY_URL=$(echo "$PREVIEW_RESPONSE" | grep -o '"play_url":"[^"]*' | grep -o '[^"]*$' | head -1)
  
  if [ -n "$PLAY_URL" ]; then
    echo "📹 Stream URL: $PLAY_URL"
    echo ""
    
    # Check for WebRTC
    if echo "$PLAY_URL" | grep -qi "webrtc"; then
      echo "✅ WebRTC DETECTED!"
      echo "   URL contains 'webrtc' - This is a WebRTC stream!"
      echo ""
      echo "   Protocol: WebRTC"
      echo "   Latency: < 1 second (real-time)"
      echo "   iOS Support: Native with flutter_webrtc package"
      echo "   Recommendation: Implement WebRTC player for best performance!"
    elif echo "$PLAY_URL" | grep -q "^ws://"; then
      echo "⚠️ WebSocket Stream"
      echo "   Protocol: ws://"
      echo "   Format: HTTP-FLV or custom"
      echo "   iOS Support: Requires WebView or media_kit"
    elif echo "$PLAY_URL" | grep -q "^wss://"; then
      echo "⚠️ Secure WebSocket Stream"
      echo "   Protocol: wss://"
      echo "   Format: HTTP-FLV or custom"
      echo "   iOS Support: Requires WebView or media_kit"
    elif echo "$PLAY_URL" | grep -q ".m3u8"; then
      echo "✅ HLS Stream"
      echo "   Protocol: HLS (HTTP Live Streaming)"
      echo "   Format: .m3u8"
      echo "   iOS Support: Native video_player package"
    elif echo "$PLAY_URL" | grep -q "^rtsp://"; then
      echo "⚠️ RTSP Stream"
      echo "   Protocol: rtsp://"
      echo "   iOS Support: Requires media_kit or VLC"
    elif echo "$PLAY_URL" | grep -q "^http.*\.flv"; then
      echo "⚠️ HTTP-FLV Stream"
      echo "   Protocol: HTTP-FLV"
      echo "   iOS Support: Requires WebView or media_kit"
    else
      echo "❓ Unknown Format"
      echo "   URL: $PLAY_URL"
    fi
  else
    echo "❌ No play_url found in response"
  fi
  
  echo ""
  
  # Close preview
  curl -s -X POST "${BASE_URL}/media/preview/close?device_id=18270761136" \
    -H "Authorization: Bearer $TOKEN" > /dev/null
  
  sleep 2
done

echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""
echo "If WebRTC was detected:"
echo "  → Best solution: flutter_webrtc package"
echo "  → Latency: < 1 second (real-time)"
echo "  → Native iOS support"
echo ""
echo "If WebSocket/HTTP-FLV was detected:"
echo "  → Current solution: WebView (works)"
echo "  → Better solution: media_kit package"
echo "  → Latency: 5-10 seconds"
echo ""

