# Deployment Information

## Public URL
https://ai-agent-vinu.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
```bash
curl https://ai-agent-vinu.railway.app/health
# Expected: {"status": "ok", "version": "1.0.0", ...}
```

### API Test (with authentication)
```bash
curl -X POST https://ai-agent-vinu.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello, are you running on cloud?"}'
```

## Environment Variables Set
- `PORT`: 8000
- `REDIS_URL`: (Tự động cấp bởi Railway Redis)
- `AGENT_API_KEY`: (Sử dụng key của bạn)
- `LOG_LEVEL`: info
- `ENVIRONMENT`: production

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
