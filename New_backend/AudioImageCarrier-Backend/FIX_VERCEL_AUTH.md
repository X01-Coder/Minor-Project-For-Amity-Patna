# 🔓 Fix: Disable Vercel Deployment Protection

Your API is deployed but has authentication protection enabled. Here's how to fix it:

## Method 1: Disable Protection (Recommended for Public API)

1. Go to: https://vercel.com/jeetbhardwajs-projects/audio-image-carrier-backend
2. Click **Settings** → **Deployment Protection**
3. Set to **"Off"** or **"Standard Protection"**
4. Save changes

## Method 2: Use Production Domain

Your production URL should be:
```
https://audio-image-carrier-backend.vercel.app
```

Try accessing:
```bash
curl https://audio-image-carrier-backend.vercel.app/health
```

## Method 3: Set Environment Variables

In Vercel Dashboard:
1. Go to **Settings** → **Environment Variables**
2. Add these variables for **Production**:

```
API_KEY = your-secure-api-key
UPLOAD_DIR = /tmp/uploads  
TEMP_DIR = /tmp/temp
MAX_UPLOAD_SIZE_MB = 50
CORS_ORIGINS = ["*"]
```

Generate secure API key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Testing After Fix

```bash
# Health check
curl https://audio-image-carrier-backend.vercel.app/health

# Should return:
# {"status":"healthy","version":"2.0.0","timestamp":"..."}
```

## Your API Endpoints

Once fixed, your API will be at:
- **Base URL**: `https://audio-image-carrier-backend.vercel.app`
- **Encode**: `POST /api/v1/encode`
- **Decode**: `POST /api/v1/decode`
- **Health**: `GET /health`
- **Docs**: `GET /docs`

## Quick Test After Fixing

```python
import requests

API_URL = "https://audio-image-carrier-backend.vercel.app"
API_KEY = "your-api-key"  # From environment variables

# Test health
response = requests.get(f"{API_URL}/health")
print(response.json())
```

---

**Next Steps:**
1. Disable deployment protection in Vercel dashboard
2. Set environment variables
3. Test the health endpoint
4. Start using the API!
