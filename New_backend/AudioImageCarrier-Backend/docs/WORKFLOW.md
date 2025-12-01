# Workflow of AudioImageCarrier Backend

## Overview
The AudioImageCarrier backend provides a FastAPI application that allows users to securely encode audio files into encrypted PNG images and decode them back into audio files. This process utilizes steganography and AES-GCM encryption to ensure data security.

## Workflow Steps

1. **User Uploads Audio File**:
   - The user sends a POST request to the `/api/encode` endpoint with the audio file and user ID.
   - The user ID (e.g., "prince") is used to derive a unique encryption key for the user, ensuring that even if multiple users use the same master key, their data remains distinct.

2. **Encoding Process**:
   - The backend processes the audio file:
     - If the audio file is a WAV file shorter than 8 hours, it is encoded as a single PNG image.
     - For larger files or other formats, the audio is split into chunks, optionally compressed, and then encrypted.
   - The encrypted data is packed into PNG images, which are then saved to the server.

3. **Response with Encoded Images**:
   - The server responds with a ZIP file containing the encoded PNG images.
   - The user can download this ZIP file for storage or further use.

4. **User Uploads PNG Images**:
   - To decode the images back into audio, the user sends a POST request to the `/api/decode` endpoint with the ZIP file containing the PNG images and the user ID.

5. **Decoding Process**:
   - The backend extracts the encrypted payload from the images, decrypts it using the user-specific key derived from the master key and user ID, and reconstructs the original audio file.
   - The recovered audio file is then sent back to the user.

6. **Response with Recovered Audio**:
   - The server responds with the recovered audio file, allowing the user to download it.

## User Parameter Explanation
The "user" parameter is crucial for security. It is used to derive a unique encryption key for each user, ensuring that even if two users use the same master key, their encrypted data remains secure and distinct. The user ID is combined with the master key to generate a user-specific key using HKDF (HMAC-based Key Derivation Function).

## API Calls

### 1. Encode Audio to Image
- **Endpoint**: POST `/api/encode`
- **Request Body**: 
  - `audio_file`: The audio file to be encoded (multipart/form-data).
  - `user`: The user ID (e.g., "prince").
  - `master_key`: The master key in hexadecimal format (optional if set in environment).
- **Response**: Returns a ZIP file containing the encoded PNG images.

### 2. Decode Image to Audio
- **Endpoint**: POST `/api/decode`
- **Request Body**: 
  - `image_files`: The ZIP file containing the PNG images (multipart/form-data).
  - `user`: The user ID (e.g., "prince").
  - `master_key`: The master key in hexadecimal format (optional if set in environment).
- **Response**: Returns the recovered audio file.

## Documentation
- **API_DOCUMENTATION.md**: Contains detailed information about each API endpoint, including request and response formats, status codes, and example requests.
- **USER_GUIDE.md**: Provides a step-by-step guide on how to set up and use the API, including example API calls.
- **WORKFLOW.md**: Describes the overall workflow of the application, detailing how audio files are processed and converted through the API.

This structured approach ensures clarity and security in handling audio files, making it easier for users to interact with the AudioImageCarrier backend.