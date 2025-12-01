# EchoCipher API Reference

## Base URL
```
http://localhost:3000
```

## Endpoints

## ✅ Health & Status

#### Check Backend Health
```
GET /health
```
**Response**:
```json
{
  "status": "ok",
  "timestamp": "2025-11-15T04:42:47.820Z",
  "uptime": 28.9857179,
  "environment": "development",
  "database": "connected"
}
```

#### API Status
```
GET /api/status
```
**Response**:
```json
{
  "message": "EchoCipher Backend API",
  "version": "1.0.0",
  "database": "connected",
  "endpoints": {
    "POST /api/convert/audio-to-image": "Convert audio to image",
    "POST /api/convert/image-to-audio": "Convert image to audio",
    "GET /api/conversions": "List all conversions",
    "GET /api/conversions/:id": "Get conversion details",
    "DELETE /api/conversions/:id": "Delete a conversion"
  }
}
```

---

### 🎵 Audio to Image Conversion

#### Convert Audio to Image
```
POST /api/convert/audio-to-image
Content-Type: multipart/form-data
```

**Parameters**:
- `audioFile` (file, required) - Audio file (.wav, .mp3, .flac, .m4a)
- `userId` (string, optional) - User identifier (default: "default-user")
- `compress` (boolean, optional) - Enable compression (default: true)
- `deleteSource` (boolean, optional) - Delete source after conversion (default: false)
- `masterKeyHex` (string, optional) - Encryption master key (uses env if not provided)

**Request**:
```bash
curl -X POST \
  -F "audioFile=@audio.wav;type=audio/wav" \
  -F "userId=user-123" \
  -F "compress=true" \
  http://localhost:3000/api/convert/audio-to-image
```

**Response (Success)**:
```json
{
  "success": true,
  "message": "Audio converted to image successfully",
  "conversionId": "085346d7-0567-496b-a995-98011f88db07",
  "inputFile": "audio.wav",
  "outputPath": "E:\\uploads\\conversions\\audio-to-image-...",
  "imageCount": 1,
  "images": ["part0001_of_0001.png"],
  "duration": 302,
  "timestamp": "2025-11-15T04:42:55.867Z"
}
```

**Response (Error)**:
```json
{
  "success": false,
  "error": "Error message",
  "message": "Audio to image conversion failed",
  "timestamp": "2025-11-15T04:42:55.867Z"
}
```

---

### 🖼️ Image to Audio Conversion

#### Convert Image to Audio
```
POST /api/convert/image-to-audio
Content-Type: application/json
```

**Request Body**:
```json
{
  "imageDirPath": "/path/to/image/directory",
  "outputFileName": "output.wav",
  "userId": "user-123"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Image converted to audio successfully",
  "conversionId": "...",
  "outputFile": "output.wav",
  "outputPath": "E:\\uploads\\conversions\\...",
  "timestamp": "2025-11-15T04:42:55.867Z"
}
```

---

### 📋 Conversion History

#### List User Conversions
```
GET /api/conversions
```

**Query Parameters** (optional):
- `userId=user-123` - Filter by user
- `status=completed` - Filter by status (pending, processing, completed, failed)
- `limit=50` - Results per page
- `skip=0` - Pagination offset

**Response**:
```json
{
  "success": true,
  "conversions": [
    {
      "conversionId": "...",
      "userId": "user-123",
      "inputFileName": "audio.wav",
      "conversionType": "audio-to-image",
      "status": "completed",
      "imageCount": 1,
      "duration": 302,
      "createdAt": "2025-11-15T04:42:55.867Z"
    }
  ],
  "total": 1,
  "timestamp": "2025-11-15T04:42:55.867Z"
}
```

#### Get Conversion Details
```
GET /api/conversions/:conversionId
```

**Response**:
```json
{
  "success": true,
  "conversion": {
    "conversionId": "...",
    "userId": "user-123",
    "inputFileName": "audio.wav",
    "inputFileSize": 176444,
    "conversionType": "audio-to-image",
    "status": "completed",
    "outputPath": "E:\\uploads\\conversions\\audio-to-image-...",
    "outputFiles": ["part0001_of_0001.png"],
    "compress": true,
    "deleteSource": false,
    "startTime": "2025-11-15T04:42:55.867Z",
    "endTime": "2025-11-15T04:43:00.867Z",
    "duration": 302,
    "metadata": { }
  },
  "timestamp": "2025-11-15T04:42:55.867Z"
}
```

---

### 📊 Statistics (Coming Soon)

#### User Statistics
```
GET /api/stats/user/:userId
```

**Response** (planned):
```json
{
  "userId": "user-123",
  "totalConversions": 10,
  "completedConversions": 9,
  "failedConversions": 1,
  "totalDataProcessed": 5242880,
  "averageConversionTime": 250
}
```

#### System Statistics
```
GET /api/admin/stats
```

**Response** (planned):
```json
{
  "totalConversions": 1000,
  "completedConversions": 950,
  "failedConversions": 50,
  "totalDataProcessed": 524288000,
  "audioToImageCount": 600,
  "imageToAudioCount": 400
}
```

---

### 🔑 Key Management (Coming Soon)

#### Create Encryption Key
```
POST /api/keys
Content-Type: application/json
```

**Request Body**:
```json
{
  "userId": "user-123",
  "keyType": "user"
}
```

#### Get User Keys
```
GET /api/keys/:userId
```

#### Rotate Key
```
POST /api/keys/:userId/rotate
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "No audio file provided",
  "message": "Please upload an audio file to convert to image",
  "timestamp": "2025-11-15T04:42:55.867Z"
}
```

### 404 Not Found
```json
{
  "error": "Not Found",
  "message": "Route POST /api/unknown not found",
  "timestamp": "2025-11-15T04:42:55.867Z"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "Python script exited with code 1: ...",
  "timestamp": "2025-11-15T04:42:55.867Z"
}
```

---

## Response Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 413 | Payload Too Large (file exceeds 500MB) |
| 500 | Internal Server Error |

---

## Limits

- **Max File Size**: 500 MB
- **Request Timeout**: 5 minutes
- **Database Connection Pool**: 5-10 connections
- **Default User Storage**: 5 GB

---

## Data Types

### Conversion Types
- `audio-to-image` - Convert audio file to PNG image(s)
- `image-to-audio` - Convert PNG image(s) to audio file

### Conversion Status
- `pending` - Waiting to be processed
- `processing` - Currently being converted
- `completed` - Successfully converted
- `failed` - Conversion error occurred

### Subscription Tiers
- `free` - Free tier (limited storage)
- `pro` - Professional tier
- `enterprise` - Enterprise tier

---

## Authentication (Coming Soon)

All endpoints will require JWT token in Authorization header:
```
Authorization: Bearer <jwt_token>
```

---

## Rate Limiting (Coming Soon)

- **Free Tier**: 10 conversions/hour
- **Pro Tier**: 100 conversions/hour
- **Enterprise**: Unlimited

---

**Last Updated**: 2025-11-15  
**Version**: 1.0.0
