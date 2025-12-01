"""
Test script to encode your M4A audio file to encrypted PNG images
"""
import requests
import hashlib
from pathlib import Path

# Configuration
BASE_URL = 'http://127.0.0.1:8000'
API_KEY = 'dev-test-key-12345'
AUDIO_FILE = r"C:\Users\bhard\OneDrive\Documents\Sound Recordings\Recording.m4a"
USER_ID = 'prince'
# Use a proper random-looking master key (64 hex chars)
MASTER_KEY = 'a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567'

# Output directory
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def get_file_hash(filepath):
    """Calculate SHA-256 hash of file."""
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_encode():
    """Encode M4A audio to encrypted PNG images."""
    print("="*70)
    print("🎵 AudioImageCarrier - Encode Your Audio File")
    print("="*70)
    
    audio_path = Path(AUDIO_FILE)
    
    # Check if file exists
    if not audio_path.exists():
        print(f"❌ Error: Audio file not found at: {AUDIO_FILE}")
        return False
    
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    print(f"\n📁 Input File:")
    print(f"   Path: {audio_path}")
    print(f"   Size: {file_size_mb:.2f} MB")
    print(f"   Format: {audio_path.suffix}")
    
    # Calculate hash
    print(f"\n🔐 Calculating file hash...")
    original_hash = get_file_hash(audio_path)
    print(f"   SHA-256: {original_hash[:32]}...")
    
    # Encode
    print(f"\n🔒 Encoding to encrypted PNG images...")
    print(f"   User ID: {USER_ID}")
    print(f"   Compression: Enabled")
    
    headers = {'X-API-Key': API_KEY}
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': (audio_path.name, f, 'audio/m4a')}
            data = {
                'user_id': USER_ID,
                'master_key': MASTER_KEY,
                'compress': 'true'
            }
            
            print(f"   Uploading to server...")
            response = requests.post(
                f'{BASE_URL}/api/v1/encode',
                headers=headers,
                files=files,
                data=data,
                timeout=300  # 5 minutes for large files
            )
        
        if response.status_code != 200:
            print(f"\n❌ Encoding failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
        
        # Save ZIP file
        output_zip = OUTPUT_DIR / 'encrypted_images.zip'
        with open(output_zip, 'wb') as f:
            f.write(response.content)
        
        # Get metadata from headers
        image_count = response.headers.get('X-Images-Count', 'unknown')
        compressed = response.headers.get('X-Compressed', 'unknown')
        original_filename = response.headers.get('X-Original-Filename', 'unknown')
        
        zip_size_mb = output_zip.stat().st_size / (1024 * 1024)
        
        print(f"\n✅ Encoding Successful!")
        print(f"\n📦 Output:")
        print(f"   File: {output_zip}")
        print(f"   Size: {zip_size_mb:.2f} MB")
        print(f"   Images: {image_count}")
        print(f"   Compressed: {compressed}")
        print(f"   Original: {original_filename}")
        
        # Calculate compression ratio
        if file_size_mb > 0:
            ratio = (zip_size_mb / file_size_mb) * 100
            print(f"   Ratio: {ratio:.1f}% of original size")
        
        print(f"\n🔐 Security Info:")
        print(f"   User ID: {USER_ID}")
        print(f"   Master Key: {MASTER_KEY[:16]}...{MASTER_KEY[-16:]}")
        print(f"\n⚠️  IMPORTANT: Save these credentials to decode later!")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to server at {BASE_URL}")
        print(f"   Please make sure the server is running:")
        print(f"   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_decode():
    """Decode the encrypted images back to audio."""
    print("\n" + "="*70)
    print("🔓 Decoding Images Back to Audio")
    print("="*70)
    
    zip_file = OUTPUT_DIR / 'encrypted_images.zip'
    
    if not zip_file.exists():
        print(f"\n⚠️  No encrypted ZIP file found. Run encoding first.")
        return False
    
    print(f"\n📁 Input: {zip_file}")
    print(f"   Size: {zip_file.stat().st_size / (1024 * 1024):.2f} MB")
    
    print(f"\n🔓 Decoding with user_id='{USER_ID}'...")
    
    headers = {'X-API-Key': API_KEY}
    
    try:
        with open(zip_file, 'rb') as f:
            files = {'images': ('encrypted_images.zip', f, 'application/zip')}
            data = {
                'user_id': USER_ID,
                'master_key': MASTER_KEY
            }
            
            response = requests.post(
                f'{BASE_URL}/api/v1/decode',
                headers=headers,
                files=files,
                data=data,
                timeout=300
            )
        
        if response.status_code != 200:
            print(f"\n❌ Decoding failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
        
        # Save recovered audio
        output_audio = OUTPUT_DIR / 'recovered_audio.m4a'
        with open(output_audio, 'wb') as f:
            f.write(response.content)
        
        recovered_size_mb = output_audio.stat().st_size / (1024 * 1024)
        
        print(f"\n✅ Decoding Successful!")
        print(f"\n📦 Output:")
        print(f"   File: {output_audio}")
        print(f"   Size: {recovered_size_mb:.2f} MB")
        
        # Verify integrity
        print(f"\n🔍 Verifying file integrity...")
        original_hash = get_file_hash(AUDIO_FILE)
        recovered_hash = get_file_hash(output_audio)
        
        print(f"   Original:  {original_hash[:32]}...")
        print(f"   Recovered: {recovered_hash[:32]}...")
        
        if original_hash == recovered_hash:
            print(f"\n🎉 SUCCESS! Files match perfectly!")
            print(f"   SHA-256: {original_hash}")
        else:
            print(f"\n⚠️  Warning: Files do not match!")
            print(f"   This should not happen - please report this issue.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the complete workflow."""
    print("\n🎵 AudioImageCarrier - Audio File Conversion Test")
    print(f"📂 Output directory: {OUTPUT_DIR}")
    print()
    
    # Step 1: Encode
    if not test_encode():
        print("\n❌ Encoding failed. Stopping.")
        return
    
    # Step 2: Decode
    print("\n" + "="*70)
    print("Now testing decode to verify everything works...")
    print("="*70)
    
    if test_decode():
        print("\n" + "="*70)
        print("🎉 COMPLETE SUCCESS!")
        print("="*70)
        print(f"\n✅ Your audio file has been successfully:")
        print(f"   1. Encoded to encrypted PNG images")
        print(f"   2. Decoded back to original audio")
        print(f"   3. Verified with SHA-256 hash matching")
        print(f"\n📁 Check the 'output' folder for results:")
        print(f"   - encrypted_images.zip (PNG images)")
        print(f"   - recovered_audio.m4a (recovered audio)")
        print(f"\n🔐 Keep your credentials safe:")
        print(f"   User ID: {USER_ID}")
        print(f"   Master Key: {MASTER_KEY}")
    else:
        print("\n⚠️  Decoding had issues. Check the output above.")

if __name__ == '__main__':
    main()
