# 🎵 AudioImageCarrier

**Encode Audio Files into Encrypted PNG Images and Decode Them Back**

AudioImageCarrier is a secure steganography tool that converts audio files into encrypted PNG images. It uses AES-GCM encryption with user-specific key derivation, optional compression, and intelligent chunking for large files.

---

## 📋 Table of Contents

- [Why Use AudioImageCarrier?](#-why-use-audioimagecarrier)
- [Features](#-features)
- [Installation](#-installation)0
- [Configuration](#-configuration)
- [Usage](#-usage)
  - [Command Line Interface (CLI)](#command-line-interface-cli)
  - [FastAPI Web Interface](#fastapi-web-interface)
- [How It Works](#-how-it-works)
- [Project Structure](#-project-structure)
- [Requirements](#-requirements)
- [Security Considerations](#-security-considerations)
- [Troubleshooting](#-troubleshooting)
- [Examples](#-examples)

---

## 🎯 Why Use AudioImageCarrier?

1. **Steganography**: Hide audio files in plain sight as PNG images
2. **Security**: AES-GCM encryption ensures your audio data is protected
3. **User-Specific Keys**: Each user gets a unique encryption key derived from a master key
4. **Compression**: Optional zstd compression reduces image file sizes
5. **Large File Support**: Intelligent chunking handles files of any size
6. **Flexible**: Works via CLI or REST API
7. **Format Agnostic**: Supports WAV, MP3, FLAC, M4A, and other audio formats

---

## ✨ Features

- ✅ **AES-GCM Encryption**: Industry-standard authenticated encryption
- ✅ **User-Specific Key Derivation**: HKDF-based key derivation per user
- ✅ **Optional Compression**: zstd compression to reduce payload size
- ✅ **Smart Chunking**: Automatically chunks large files (avoids chunking for WAV < 8 hours)
- ✅ **Sentinel Markers**: Reliable payload extraction with end-of-data markers
- ✅ **SHA-256 Verification**: Ensures data integrity during decode
- ✅ **CLI & API**: Use via command line or FastAPI web service
- ✅ **Multiple Formats**: Supports various audio formats

---

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Download the Project

```bash
cd "D:\Game Script\New-Implementations"
```

### Step 2: Install Dependencies

```bash
pip install -r requirement.txt
```

**Required packages:**
- `fastapi` - Web framework for API
- `uvicorn` - ASGI server
- `cryptography` - Encryption/decryption
- `Pillow` - Image processing
- `numpy` - Array operations
- `zstandard` - Optional compression (recommended)

---

## 🔐 Configuration

### Setting the Master Key

The master key is required for encryption/decryption. You can set it via environment variable or pass it directly as a command-line argument.

#### Option 1: Environment Variable (Recommended)

**Windows PowerShell:**
```powershell
$env:AICARRIER_MASTER_KEY_HEX = "00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"
```

**Windows CMD:**
```cmd
set AICARRIER_MASTER_KEY_HEX=00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF
```

**Linux/macOS:**
```bash
export AICARRIER_MASTER_KEY_HEX="00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"
```

**Note:** The master key must be a 64-character hexadecimal string (32 bytes = 256 bits).

#### Option 2: Command-Line Argument

You can pass the master key directly using the `--master` flag (see Usage section).

---

## 🚀 Usage

### Command Line Interface (CLI)

#### ✅ Encode Audio → Encrypted PNG Image(s)

**Basic Encoding:**
```bash
python audio_image_chunked.py encode --input "my_audio.wav" --outdir "out_images" --user "prince"
```

**With Short Flags:**
```bash
python audio_image_chunked.py encode -i "my_audio.wav" -o "out_images" -u "prince"
```

**With Master Key (if not using env variable):**
```bash
python audio_image_chunked.py encode -i "my_audio.wav" -o "out_images" -u "prince" --master "00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"
```

**Disable Compression:**
```bash
python audio_image_chunked.py encode -i "my_audio.wav" -o "out_images" -u "prince" --no-compress
```

**Custom Chunk Size (default: 50MB):**
```bash
python audio_image_chunked.py encode -i "large_audio.wav" -o "out_images" -u "prince" --max-chunk-bytes 100000000
```

**Delete Source After Encoding:**
```bash
python audio_image_chunked.py encode -i "my_audio.wav" -o "out_images" -u "prince" --delete
```

**Notes:**
- If the audio is a WAV file shorter than 8 hours, it will **not** be chunked — it will produce **1 PNG**.
- If it's larger or another format, it will chunk normally.
- Output images are named: `{basename}_part0001_of_0001.png`, `{basename}_part0002_of_0002.png`, etc.

#### ✅ Decode PNG Image(s) → Original Audio

**Basic Decoding:**
```bash
python audio_image_chunked.py decode --indir "out_images" --out "recovered.wav" --user "prince"
```

**With Short Flags:**
```bash
python audio_image_chunked.py decode -i "out_images" -o "recovered.wav" -u "prince"
```

**With Master Key:**
```bash
python audio_image_chunked.py decode -i "out_images" -o "recovered.wav" -u "prince" --master "00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"
```

#### 🔥 Quick Test Commands (Copy-Paste)

**Encode:**
```bash
python audio_image_chunked.py encode -i audio.wav -o out_images -u prince
```

**Decode:**
```bash
python audio_image_chunked.py decode -i out_images -o recovered.wav -u prince
```

---

### FastAPI Web Interface

#### Starting the API Server

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Or with reload for development:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

#### API Endpoints

##### 1. Encode Endpoint

**POST** `/encode`

Upload an audio file and receive a ZIP of encrypted PNG images.

**Headers:**
```
X-API-Key: your-api-key-here
```

**Form Data:**
- `file` (required): Audio file to encode
- `user` (required): User ID for key derivation
- `master` (optional): Master key hex (if not using env variable)
- `max_chunk_bytes` (optional): Max bytes per chunk (default: 52428800 = 50MB)
- `no_compress` (optional): Boolean to disable compression
- `delete_source` (optional): Boolean to delete source after encoding

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/encode" \
  -H "X-API-Key: dev-key" \
  -F "file=@my_audio.wav" \
  -F "user=prince" \
  -F "no_compress=false"
```

**Response:**
```json
{
  "images_zip": "my_audio_images.zip",
  "temp_dir": "/tmp/tmpXXXXXX"
}
```

##### 2. Decode Endpoint

**POST** `/decode`

Upload a ZIP of encrypted PNG images and receive the recovered audio file.

**Headers:**
```
X-API-Key: your-api-key-here
```

**Form Data:**
- `images` (required): ZIP file containing PNG images
- `user` (required): User ID used for encryption
- `master` (optional): Master key hex (if not using env variable)

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/decode" \
  -H "X-API-Key: dev-key" \
  -F "images=@out_images.zip" \
  -F "user=prince" \
  -o recovered.wav
```

**Response:** Audio file stream (WAV format)

#### Setting API Key

Set the API key via environment variable:
```bash
$env:AICARRIER_API_KEY = "your-secret-api-key"
```

Or modify `app.py` to change the default key.

---

## 🔧 How It Works

### Encoding Process

1. **Read Audio File**: Load the audio file into memory (or stream for large files)
2. **Duration Check**: For WAV files, check duration. If < 8 hours, encode as single chunk
3. **Chunking**: Split large files into chunks (default: 50MB per chunk)
4. **Compression** (optional): Compress each chunk using zstd
5. **Encryption**: 
   - Derive user-specific key from master key + user ID using HKDF
   - Encrypt chunk with AES-GCM (includes authentication tag)
6. **Payload Construction**:
   - 4-byte header length
   - JSON header (padded to 1024 bytes) containing metadata
   - 12-byte nonce
   - Encrypted ciphertext
   - 8-byte sentinel marker (`AIMGEND1`)
7. **Image Generation**: Convert payload bytes to RGB pixels (3 bytes per pixel)
8. **Save PNG**: Save as PNG image with maximum compression

### Decoding Process

1. **Load Images**: Find all PNG/TIFF images in input directory
2. **Extract Payload**: Convert image pixels back to bytes
3. **Parse Header**: Read JSON header to get metadata
4. **Find Sentinel**: Locate end-of-data marker to extract ciphertext
5. **Decryption**:
   - Derive user-specific key from master key + user ID
   - Decrypt ciphertext using AES-GCM
6. **Decompression** (if needed): Decompress if chunk was compressed
7. **Verification**: Verify SHA-256 hash matches header
8. **Reconstruct**: Write chunks to output file in order

### Security Architecture

```
Master Key (256-bit)
    ↓
HKDF-SHA256 (salt: None, info: "AUDIO-IMG-V1")
    ↓
User Key (256-bit) = HKDF(Master Key + User ID)
    ↓
AES-GCM Encryption (12-byte nonce, authenticated encryption)
    ↓
Encrypted Payload + Authentication Tag
```

---

## 📁 Project Structure

```
New-Implementations/
├── audio_image_chunked.py    # Main CLI script (encode/decode)
├── app.py                     # FastAPI web service
├── requirement.txt            # Python dependencies
└── README.md                  # This file
```

---

## 📋 Requirements

See `requirement.txt` for the complete list. Key dependencies:

- **fastapi** >= 0.104.0, < 0.110.0
- **uvicorn[standard]** >= 0.24.0, < 0.30.0
- **cryptography** >= 41.0.0, < 43.0.0
- **Pillow** >= 10.0.0, < 11.0.0
- **numpy** >= 1.24.0, < 2.0.0
- **zstandard** >= 0.22.0, < 0.24.0 (optional but recommended)

---

## 🔒 Security Considerations

1. **Master Key Security**: 
   - Never commit the master key to version control
   - Use environment variables or secure key management
   - Rotate keys periodically

2. **User ID**: 
   - User IDs should be unique per user
   - Don't use predictable user IDs (e.g., sequential numbers)

3. **Nonce Uniqueness**: 
   - Each chunk uses a random 12-byte nonce
   - Nonces are generated using `os.urandom()` (cryptographically secure)

4. **Authentication**: 
   - AES-GCM provides authenticated encryption
   - SHA-256 verification ensures data integrity

5. **API Security**: 
   - Change the default API key in production
   - Use HTTPS in production
   - Implement rate limiting and authentication

---

## 🐛 Troubleshooting

### Error: "Master key required"

**Solution:** Set the `AICARRIER_MASTER_KEY_HEX` environment variable or pass `--master` flag.

### Error: "Decryption failed"

**Possible causes:**
- Wrong master key
- Wrong user ID
- Corrupted image file
- Incorrect chunk order

**Solution:** Verify master key and user ID match the encoding parameters.

### Error: "SHA mismatch"

**Cause:** Data corruption or incorrect decryption.

**Solution:** Re-encode the audio file or check for image corruption.

### Images are too large

**Solution:** 
- Enable compression (remove `--no-compress` flag)
- Reduce chunk size with `--max-chunk-bytes`
- Use a more efficient audio format

### WAV duration detection fails

**Note:** Duration detection only works for uncompressed WAV files. For other formats (MP3, FLAC, M4A), the file will be chunked normally.

---

## 💡 Examples

### Example 1: Encode a Short Audio File

```bash
# Set master key
$env:AICARRIER_MASTER_KEY_HEX = "00112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF"

# Encode (produces 1 PNG for WAV < 8 hours)
python audio_image_chunked.py encode -i "song.wav" -o "images" -u "alice"

# Decode
python audio_image_chunked.py decode -i "images" -o "recovered.wav" -u "alice"
```

### Example 2: Encode a Large Audio File

```bash
# Encode with custom chunk size (100MB per chunk)
python audio_image_chunked.py encode -i "podcast.mp3" -o "podcast_images" -u "bob" --max-chunk-bytes 100000000

# Decode (automatically finds and orders all chunks)
python audio_image_chunked.py decode -i "podcast_images" -o "podcast_recovered.mp3" -u "bob"
```

### Example 3: Using the API

```bash
# Start server
uvicorn app:app --host 0.0.0.0 --port 8000

# Encode via API
curl -X POST "http://localhost:8000/encode" \
  -H "X-API-Key: dev-key" \
  -F "file=@audio.wav" \
  -F "user=prince" \
  -o images.zip

# Decode via API
curl -X POST "http://localhost:8000/decode" \
  -H "X-API-Key: dev-key" \
  -F "images=@images.zip" \
  -F "user=prince" \
  -o recovered.wav
```

---

## 📊 Technical Details

### Image Format

- **Format**: PNG (RGB, 24-bit)
- **Max Width**: 8192 pixels (configurable)
- **Compression**: PNG level 9 (maximum)

### Payload Structure

```
[4 bytes: header length]
[1024 bytes: JSON header (padded with zeros)]
[12 bytes: AES-GCM nonce]
[variable: encrypted ciphertext + 16-byte tag]
[8 bytes: sentinel "AIMGEND1"]
```

### Header JSON Fields

```json
{
  "magic": "AUDIO-IMG-V1",
  "version": 1,
  "user_id": "prince",
  "orig_filename": "audio.wav",
  "orig_chunk_index": 0,
  "orig_total_chunks": 1,
  "orig_chunk_size": 1234567,
  "ts": 1234567890,
  "compressed": true,
  "sha256": "abc123..."
}
```

---

## 📝 License

This project is provided as-is for educational and research purposes.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

---

## 📧 Support

For issues or questions, please open an issue in the project repository.

---

**Made with ❤️ for secure audio steganography**

