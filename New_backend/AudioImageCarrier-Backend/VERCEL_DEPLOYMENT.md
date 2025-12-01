# AudioImageCarrier API - Vercel Deployment Guide

## 🚀 Quick Deploy to Vercel

### Step 1: Prepare Your Project

1. **Install Vercel CLI** (optional, or use Vercel dashboard):
```bash
npm install -g vercel
```

2. **Update dependencies** for Vercel (already done):
- `vercel.json` configured
- `api/index.py` entry point created
- Requirements.txt ready

### Step 2: Deploy to Vercel

**Option A: Using Vercel CLI**
```bash
cd "E:\Projects\minnor Project\New_backend\AudioImageCarrier-Backend"
vercel
```

**Option B: Using Vercel Dashboard**
1. Go to https://vercel.com
2. Click "Add New Project"
3. Import your Git repository (or upload folder)
4. Vercel will auto-detect Python
5. Click "Deploy"

### Step 3: Set Environment Variables

In Vercel Dashboard → Settings → Environment Variables, add:

```
API_KEY = your-secure-random-api-key-here
UPLOAD_DIR = /tmp/uploads
TEMP_DIR = /tmp/temp
MAX_UPLOAD_SIZE_MB = 100
CORS_ORIGINS = ["*"]
```

**Generate secure API key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 📖 How to Use the API

### Your Deployed API URL
After deployment, Vercel gives you a URL like:
```
https://your-project-name.vercel.app
```

### API Documentation
Once deployed, visit:
- **Swagger UI**: `https://your-project-name.vercel.app/docs`
- **ReDoc**: `https://your-project-name.vercel.app/redoc`

---

## 🔧 API Usage Examples

### 1. Encode Audio to Images (Python)

```python
import requests

API_URL = "https://your-project-name.vercel.app"
API_KEY = "your-api-key-here"

# Upload audio file
with open("audio.m4a", "rb") as f:
    response = requests.post(
        f"{API_URL}/api/v1/encode",
        headers={"X-API-Key": API_KEY},
        files={"file": ("audio.m4a", f, "audio/m4a")},
        data={
            "user_id": "prince",
            "master_key": "a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567",
            "compress": "true"
        }
    )

# Save encrypted images ZIP
with open("encrypted_images.zip", "wb") as f:
    f.write(response.content)

print("✅ Encoded successfully!")
```

### 2. Decode Images to Audio (Python)

```python
import requests

API_URL = "https://your-project-name.vercel.app"
API_KEY = "your-api-key-here"

# Upload ZIP file
with open("encrypted_images.zip", "rb") as f:
    response = requests.post(
        f"{API_URL}/api/v1/decode",
        headers={"X-API-Key": API_KEY},
        files={"images": ("encrypted_images.zip", f, "application/zip")},
        data={
            "user_id": "prince",
            "master_key": "a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567"
        }
    )

# Save recovered audio
with open("recovered_audio.m4a", "wb") as f:
    f.write(response.content)

print("✅ Decoded successfully!")
```

### 3. Using JavaScript/TypeScript (Frontend)

```javascript
// Encode Audio
async function encodeAudio(audioFile) {
  const formData = new FormData();
  formData.append('file', audioFile);
  formData.append('user_id', 'prince');
  formData.append('master_key', 'a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567');
  formData.append('compress', 'true');

  const response = await fetch('https://your-project-name.vercel.app/api/v1/encode', {
    method: 'POST',
    headers: {
      'X-API-Key': 'your-api-key-here'
    },
    body: formData
  });

  const blob = await response.blob();
  // Download or use the ZIP file
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'encrypted_images.zip';
  a.click();
}

// Decode Images
async function decodeImages(zipFile) {
  const formData = new FormData();
  formData.append('images', zipFile);
  formData.append('user_id', 'prince');
  formData.append('master_key', 'a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567');

  const response = await fetch('https://your-project-name.vercel.app/api/v1/decode', {
    method: 'POST',
    headers: {
      'X-API-Key': 'your-api-key-here'
    },
    body: formData
  });

  const blob = await response.blob();
  // Download or play the audio
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'recovered_audio.m4a';
  a.click();
}
```

### 4. Using cURL (Command Line)

```bash
# Encode
curl -X POST "https://your-project-name.vercel.app/api/v1/encode" \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@audio.m4a" \
  -F "user_id=prince" \
  -F "master_key=a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567" \
  -F "compress=true" \
  -o encrypted_images.zip

# Decode
curl -X POST "https://your-project-name.vercel.app/api/v1/decode" \
  -H "X-API-Key: your-api-key-here" \
  -F "images=@encrypted_images.zip" \
  -F "user_id=prince" \
  -F "master_key=a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567" \
  -o recovered_audio.m4a
```

---

## 🔐 Security Best Practices

### 1. Protect Your API Key
```javascript
// ❌ Don't do this (client-side)
const API_KEY = "your-api-key-here"; // Exposed to users!

// ✅ Do this instead
// Call your own backend which has the API key
const response = await fetch('/your-backend/encode', {
  method: 'POST',
  body: formData
});
```

### 2. Use Unique Master Keys Per User
```python
# ❌ Don't share keys
master_key = "same-key-for-everyone"  # Insecure!

# ✅ Each user gets unique key
import hashlib
master_key = hashlib.sha256(f"{user_id}:{secret_salt}".encode()).hexdigest()
```

### 3. Store Master Keys Securely
- Use database encryption
- Use environment variables
- Use secret management services (AWS Secrets Manager, etc.)

---

## 📱 Complete React Example

```jsx
import React, { useState } from 'react';

function AudioEncoder() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const API_URL = "https://your-project-name.vercel.app";
  const API_KEY = "your-api-key-here";
  const USER_ID = "prince";
  const MASTER_KEY = "a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567";

  const handleEncode = async () => {
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', USER_ID);
    formData.append('master_key', MASTER_KEY);
    formData.append('compress', 'true');

    try {
      const response = await fetch(`${API_URL}/api/v1/encode`, {
        method: 'POST',
        headers: { 'X-API-Key': API_KEY },
        body: formData
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        setResult(url);
      } else {
        alert('Encoding failed: ' + await response.text());
      }
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>🎵 Audio to Encrypted Images</h2>
      <input
        type="file"
        accept="audio/*"
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button onClick={handleEncode} disabled={!file || loading}>
        {loading ? 'Encoding...' : 'Encode Audio'}
      </button>
      {result && (
        <div>
          <p>✅ Encoded successfully!</p>
          <a href={result} download="encrypted_images.zip">
            Download Encrypted ZIP
          </a>
        </div>
      )}
    </div>
  );
}

export default AudioEncoder;
```

---

## 🎯 API Endpoints Reference

### POST /api/v1/encode
Convert audio file to encrypted PNG images.

**Headers:**
- `X-API-Key`: Your API key (required)

**Form Data:**
- `file`: Audio file (required)
- `user_id`: User identifier (required)
- `master_key`: 64 hex characters (required)
- `compress`: true/false (optional, default: true)

**Response:**
- ZIP file containing encrypted PNG images

---

### POST /api/v1/decode
Convert encrypted images back to audio.

**Headers:**
- `X-API-Key`: Your API key (required)

**Form Data:**
- `images`: ZIP file with PNG images (required)
- `user_id`: Same as encoding (required)
- `master_key`: Same as encoding (required)

**Response:**
- Original audio file

---

### GET /health
Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-11-20T12:00:00"
}
```

---

## ⚠️ Important Notes for Vercel

### File Size Limits
Vercel has limits:
- **Request body**: 4.5 MB (Hobby), 100 MB (Pro)
- **Function timeout**: 10s (Hobby), 60s (Pro)

For large files, consider:
1. Upgrade to Vercel Pro
2. Use AWS S3 + Lambda
3. Self-host on VPS

### Temporary Storage
Vercel uses `/tmp` which is:
- Limited to 512 MB
- Cleared between requests
- Not persistent

The API handles cleanup automatically.

---

## 🔄 Testing Your Deployed API

```bash
# Test health check
curl https://your-project-name.vercel.app/health

# Test with small audio file
curl -X POST "https://your-project-name.vercel.app/api/v1/encode" \
  -H "X-API-Key: your-api-key" \
  -F "file=@small-audio.mp3" \
  -F "user_id=test" \
  -F "master_key=a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567" \
  -o output.zip
```

---

## 📞 Support & Documentation

- **Full API Docs**: `https://your-project-name.vercel.app/docs`
- **GitHub**: Your repository URL
- **Issues**: Report bugs in GitHub Issues

---

## ✅ Deployment Checklist

- [ ] Created Vercel account
- [ ] Installed Vercel CLI or prepared Git repo
- [ ] Set environment variables in Vercel
- [ ] Generated secure API key
- [ ] Tested deployment with small files
- [ ] Updated CORS origins if needed
- [ ] Documented API key for your team
- [ ] Tested from your frontend/app

---

**Your API is ready to use! 🎉**

Start building amazing audio encryption features in your apps!
