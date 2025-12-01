# USER GUIDE for AudioImageCarrier Backend

## Overview

The AudioImageCarrier backend provides a FastAPI-based service that allows users to securely encode audio files into encrypted PNG images and decode them back into audio files. This guide will help you understand how to set up and use the API effectively.

## Setup Instructions

1. **Clone the Repository**
   Clone the project repository to your local machine:
   ```
   git clone <repository-url>
   cd AudioImageCarrier-Backend
   ```

2. **Install Dependencies**
   Ensure you have Python 3.8 or higher installed. Then, install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**
   Create a `.env` file based on the `.env.example` provided in the root directory. Set your master key in hexadecimal format:
   ```
   AICARRIER_MASTER_KEY_HEX=your_master_key_here
   ```

4. **Run the Application**
   Start the FastAPI application:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## API Usage

### Encode Audio to Image

- **Endpoint**: `POST /api/encode`
- **Description**: This endpoint encodes an audio file into one or more encrypted PNG images.
- **Request Body**:
  - `audio_file`: The audio file to be encoded (multipart/form-data).
  - `user`: The user ID (e.g., "prince").
  - `master_key`: The master key in hexadecimal format (optional if set in environment).

- **Example cURL Command**:
  ```
  curl -X POST "http://localhost:8000/api/encode" \
    -F "audio_file=@path_to_your_audio_file.wav" \
    -F "user=prince" \
    -F "master_key=00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"
  ```

- **Response**: Returns a ZIP file containing the encoded PNG images.

### Decode Image to Audio

- **Endpoint**: `POST /api/decode`
- **Description**: This endpoint decodes a ZIP file of encrypted PNG images back into the original audio file.
- **Request Body**:
  - `image_files`: The ZIP file containing the PNG images (multipart/form-data).
  - `user`: The user ID (e.g., "prince").
  - `master_key`: The master key in hexadecimal format (optional if set in environment).

- **Example cURL Command**:
  ```
  curl -X POST "http://localhost:8000/api/decode" \
    -F "image_files=@path_to_your_images.zip" \
    -F "user=prince" \
    -F "master_key=00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"
  ```

- **Response**: Returns the recovered audio file.

## User Parameter Explanation

The `user` parameter (e.g., "prince") is crucial for security. It is used to derive a unique encryption key for each user. This ensures that even if two users use the same master key, their encrypted data remains secure and distinct. The user ID is combined with the master key to generate a user-specific key using HKDF (HMAC-based Key Derivation Function).

## Additional Documentation

- **API_DOCUMENTATION.md**: Contains detailed information about each API endpoint, including request and response formats, status codes, and example requests.
- **WORKFLOW.md**: Describes the overall workflow of the application, detailing how audio files are processed and converted through the API.

This guide should help you get started with the AudioImageCarrier backend and utilize its features effectively. For further assistance, please refer to the additional documentation or open an issue in the project repository.