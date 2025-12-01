# AudioImageCarrier API - Testing Guide

## ✅ Backend Status
The backend is **COMPLETE** and **READY FOR TESTING**!

## 🚀 Starting the Server

### Option 1: Command Line
```bash
cd "E:\Projects\minnor Project\New_backend\AudioImageCarrier-Backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Option 2: Direct Python
```bash
python -m app.main
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started server process [XXXX]
✅ AudioImageCarrier API v2.0.0 started
📁 Upload directory: storage/uploads
📁 Temp directory: storage/temp
INFO:     Application startup complete.
```

## 📖 Interactive Documentation
Once the server is running, visit:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## 🧪 Testing with Python

### 1. Health Check
```python
import requests

BASE_URL = 'http://127.0.0.1:8000'
API_KEY = 'dev-test-key-12345'

# Test health endpoint
response = requests.get(f'{BASE_URL}/health')
print(response.json())
# Expected: {"status": "healthy", "version": "2.0.0", "timestamp": "..."}
```

### 2. Test Encode Endpoint

```python
import requests
from pathlib import Path

BASE_URL = 'http://127.0.0.1:8000'
API_KEY = 'dev-test-key-12345'
headers = {'X-API-Key': API_KEY}

# Prepare test audio file
audio_file = 'path/to/your/audio.wav'

# Encode request
with open(audio_file, 'rb') as f:
    files = {'file': ('audio.wav', f, 'audio/wav')}
    data = {
        'user_id': 'prince',
        'master_key': '0123456789abcdef' * 4,  # 64 hex characters
        'compress': 'true',
        'max_chunk_bytes': '52428800'  # 50MB
    }
    
    response = requests.post(
        f'{BASE_URL}/api/v1/encode',
        headers=headers,
        files=files,
        data=data
    )

# Save encrypted images ZIP
if response.status_code == 200:
    with open('encrypted_images.zip', 'wb') as f:
        f.write(response.content)
    print("✅ Encoding successful!")
    print(f"File size: {len(response.content)} bytes")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.json())
```

### 3. Test Decode Endpoint

```python
import requests

BASE_URL = 'http://127.0.0.1:8000'
API_KEY = 'dev-test-key-12345'
headers = {'X-API-Key': API_KEY}

# Decode request
with open('encrypted_images.zip', 'rb') as f:
    files = {'images': ('encrypted_images.zip', f, 'application/zip')}
    data = {
        'user_id': 'prince',
        'master_key': '0123456789abcdef' * 4,  # Same as encoding!
    }
    
    response = requests.post(
        f'{BASE_URL}/api/v1/decode',
        headers=headers,
        files=files,
        data=data
    )

# Save recovered audio
if response.status_code == 200:
    with open('recovered_audio.wav', 'wb') as f:
        f.write(response.content)
    print("✅ Decoding successful!")
    print(f"File size: {len(response.content)} bytes")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.json())
```

## 🧪 Testing with cURL

### Health Check
```bash
curl http://127.0.0.1:8000/health
```

### Encode Audio to Images
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/encode" \
  -H "X-API-Key: dev-test-key-12345" \
  -F "file=@audio.wav" \
  -F "user_id=prince" \
  -F "master_key=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" \
  -F "compress=true" \
  -o encrypted_images.zip
```

### Decode Images to Audio
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/decode" \
  -H "X-API-Key: dev-test-key-12345" \
  -F "images=@encrypted_images.zip" \
  -F "user_id=prince" \
  -F "master_key=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" \
  -o recovered_audio.wav
```

## 🧪 Testing with Swagger UI (Recommended)

1. **Open Browser**: Navigate to http://127.0.0.1:8000/docs
2. **Authorize**: Click "Authorize" button, enter API key: `dev-test-key-12345`
3. **Test Encode**:
   - Click on `/api/v1/encode`
   - Click "Try it out"
   - Upload audio file
   - Fill in parameters:
     - `user_id`: prince
     - `master_key`: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
     - `compress`: true
   - Click "Execute"
   - Download the ZIP file from response

4. **Test Decode**:
   - Click on `/api/v1/decode`
   - Click "Try it out"
   - Upload the ZIP file from previous step
   - Fill in same `user_id` and `master_key`
   - Click "Execute"
   - Download the recovered audio file

## 🧪 Security Testing

### Test 1: Invalid API Key
```python
# Should return 403 Forbidden
response = requests.get(
    'http://127.0.0.1:8000/health',
    headers={'X-API-Key': 'wrong-key'}
)
print(response.status_code)  # Expected: 403
```

### Test 2: Missing API Key
```python
# Should return 401/403
response = requests.post('http://127.0.0.1:8000/api/v1/encode')
print(response.status_code)  # Expected: 401 or 403
```

### Test 3: Wrong User ID on Decode
```python
# Encode with user_id="alice"
# Try to decode with user_id="bob"
# Should fail - cannot decrypt with different user_id
```

### Test 4: Wrong Master Key
```python
# Encode with one master_key
# Try to decode with different master_key
# Should fail - decryption error
```

## 📊 Expected Results

### Successful Encode Response
- **Status Code**: 200
- **Content-Type**: application/zip
- **Headers**:
  - `X-Images-Count`: Number of PNG images
  - `X-Original-Filename`: Original audio filename
  - `X-Compressed`: true/false
- **Body**: ZIP file containing PNG images

### Successful Decode Response
- **Status Code**: 200
- **Content-Type**: audio/wav (or original format)
- **Headers**:
  - `Content-Disposition`: attachment; filename="recovered_audio.wav"
  - `X-Original-Format`: Original audio format
- **Body**: Recovered audio file (should match original exactly!)

### Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Missing API Key"
}
```

#### 403 Forbidden
```json
{
  "detail": "Invalid API Key"
}
```

#### 400 Bad Request
```json
{
  "success": false,
  "error": "ValidationError",
  "message": "Invalid user_id or master_key format"
}
```

#### 500 Internal Server Error
```json
{
  "success": false,
  "error": "DecryptionError",
  "message": "Decryption failed - check user_id and master_key"
}
```

## 🎯 Test Checklist

- [ ] Server starts without errors
- [ ] `/health` endpoint returns 200
- [ ] `/` endpoint returns API info
- [ ] Swagger UI loads at `/docs`
- [ ] Can encode small audio file (< 1MB)
- [ ] Encoded ZIP contains PNG images
- [ ] Can decode back to original audio
- [ ] Decoded audio matches original (compare file hashes)
- [ ] Test with compression enabled
- [ ] Test with compression disabled
- [ ] Test with different user_ids
- [ ] Test authentication (invalid API key fails)
- [ ] Test wrong user_id on decode (fails)
- [ ] Test wrong master_key on decode (fails)
- [ ] Test large audio file (> 10MB)
- [ ] Verify automatic chunking works
- [ ] Check cleanup of temp files after request

## 🔍 Verification Commands

### Compare Files (SHA-256)
```python
import hashlib

def get_file_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

original_hash = get_file_hash('original_audio.wav')
recovered_hash = get_file_hash('recovered_audio.wav')

if original_hash == recovered_hash:
    print("✅ Files match perfectly!")
else:
    print("❌ Files do not match!")
```

### Check PNG Images
```python
from PIL import Image
from zipfile import ZipFile

with ZipFile('encrypted_images.zip', 'r') as zf:
    print(f"Images in ZIP: {len(zf.namelist())}")
    for name in zf.namelist():
        with Image.open(zf.open(name)) as img:
            print(f"  {name}: {img.size} ({img.mode})")
```

## 🐛 Troubleshooting

### Server won't start
- Check if port 8000 is already in use
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (need 3.10+)

### Import errors
- Ensure you're in the project root directory
- Check `.env` file exists with correct settings

### Decryption fails
- Verify you're using the SAME `user_id` and `master_key` for encode and decode
- Check `master_key` is exactly 64 hexadecimal characters
- Ensure user_id contains only alphanumeric and underscores

### Files don't match
- This should NEVER happen! If it does, there's a bug
- Check if compression settings were the same
- Verify no errors in server logs

## 📝 Creating Test Audio File

If you don't have an audio file, create one with Python:

```python
import numpy as np
from scipy.io import wavfile

# Generate 1 second of 440Hz sine wave
sample_rate = 44100
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration))
audio = np.sin(2 * np.pi * 440 * t) * 32767
audio = audio.astype(np.int16)

# Save as WAV
wavfile.write('test_audio.wav', sample_rate, audio)
print("✅ test_audio.wav created!")
```

Or use this simpler version without scipy:

```python
import wave
import struct
import math

sample_rate = 44100
duration = 1.0
frequency = 440  # A4 note

with wave.open('test_audio.wav', 'w') as wav_file:
    wav_file.setnchannels(1)  # Mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(sample_rate)
    
    for i in range(int(sample_rate * duration)):
        value = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
        wav_file.writeframes(struct.pack('h', value))

print("✅ test_audio.wav created!")
```

## 🚀 Production Deployment Notes

Before deploying to production:

1. **Change API Key**: Update `API_KEY` in `.env` to a strong random value
2. **Use HTTPS**: Deploy behind reverse proxy (nginx) with SSL
3. **Rate Limiting**: Add rate limiting middleware
4. **File Size Limits**: Adjust `MAX_UPLOAD_SIZE_MB` based on needs
5. **CORS**: Update `CORS_ORIGINS` to your actual frontend URLs
6. **Master Keys**: Each user MUST have unique master_key (don't share!)
7. **Monitoring**: Add logging and error tracking (Sentry, etc.)
8. **Storage**: Consider using cloud storage (S3) for large files
9. **Database**: Add database for user management and audit logs

## 📖 API Documentation

Full API documentation with examples is available in `docs/API_DOCUMENTATION.md`

---

**Status**: ✅ Backend Complete - Ready for Testing!
**Version**: 2.0.0
**Last Updated**: 2024
