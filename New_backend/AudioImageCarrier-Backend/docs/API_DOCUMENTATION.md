# API Documentation for AudioImageCarrier Backend

## Overview

The AudioImageCarrier backend provides APIs for encoding audio files into encrypted PNG images and decoding those images back into audio files. This document outlines the available endpoints, request/response formats, and example calls.

## User Parameter Explanation

The "user" parameter (e.g., "prince") is used to derive a unique encryption key for each user. This ensures that even if two users use the same master key, their encrypted data remains secure and distinct. The user ID is combined with the master key to generate a user-specific key using HKDF (HMAC-based Key Derivation Function).

## API Endpoints

### 1. Encode Audio to Image

- **Endpoint**: `POST /api/encode`
- **Description**: This endpoint encodes an audio file into encrypted PNG images.
  
#### Request Body

- **audio_file**: The audio file to be encoded (multipart/form-data).
- **user**: The user ID (e.g., "prince").
- **master_key**: The master key in hexadecimal format (optional if set in environment).

#### Response

- **Content**: Returns a ZIP file containing the encoded PNG images.
- **Status Codes**:
  - `200 OK`: Successfully encoded the audio file.
  - `400 Bad Request`: Invalid input or missing parameters.
  - `500 Internal Server Error`: An error occurred during processing.

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/encode" \
  -F "audio_file=@path/to/audio.wav" \
  -F "user=prince" \
  -F "master_key=00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"
```

### 2. Decode Image to Audio

- **Endpoint**: `POST /api/decode`
- **Description**: This endpoint decodes PNG images back into the original audio file.

#### Request Body

- **image_files**: The ZIP file containing the PNG images (multipart/form-data).
- **user**: The user ID (e.g., "prince").
- **master_key**: The master key in hexadecimal format (optional if set in environment).

#### Response

- **Content**: Returns the recovered audio file.
- **Status Codes**:
  - `200 OK`: Successfully decoded the images into audio.
  - `400 Bad Request`: Invalid input or missing parameters.
  - `500 Internal Server Error`: An error occurred during processing.

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/decode" \
  -F "image_files=@path/to/images.zip" \
  -F "user=prince" \
  -F "master_key=00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF" \
  -o recovered_audio.wav
```

## Documentation Files

- **API_DOCUMENTATION.md**: Contains detailed information about each API endpoint, including request and response formats, status codes, and example requests.
- **USER_GUIDE.md**: Provides a step-by-step guide on how to set up and use the API, including example API calls.
- **WORKFLOW.md**: Describes the overall workflow of the application, detailing how audio files are processed and converted through the API.

This structure allows for a clear separation of concerns, making it easier to maintain and extend the application in the future.