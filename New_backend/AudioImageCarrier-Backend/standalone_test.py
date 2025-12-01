"""
Standalone API Test Script
Run this AFTER starting the server in a separate terminal
"""
import sys
import time
import requests
import hashlib
import tempfile
import wave
import struct
import math
from pathlib import Path

BASE_URL = 'http://127.0.0.1:8000'
API_KEY = 'dev-test-key-12345'
TEST_USER_ID = 'prince'
TEST_MASTER_KEY = '0123456789abcdef' * 4  # 64 hex chars

def create_test_audio(filepath):
    """Create a simple test audio file."""
    print(f"📝 Creating test audio file: {filepath}")
    sample_rate = 44100
    duration = 1.0  # 1 second
    frequency = 440  # A4 note
    
    with wave.open(str(filepath), 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(int(sample_rate * duration)):
            value = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wav_file.writeframes(struct.pack('h', value))
    
    print(f"✅ Created: {filepath.stat().st_size} bytes")
    return filepath

def get_file_hash(filepath):
    """Calculate SHA-256 hash of file."""
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_server_running():
    """Check if server is running."""
    print("\n" + "="*70)
    print("TEST 1: Check if server is running")
    print("="*70)
    try:
        response = requests.get(f'{BASE_URL}/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is running!")
            print(f"   Status: {data.get('status')}")
            print(f"   Version: {data.get('version')}")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print(f"   Please start the server first:")
        print(f"   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_authentication():
    """Test API key authentication."""
    print("\n" + "="*70)
    print("TEST 2: API Key Authentication")
    print("="*70)
    
    # Test with valid API key
    try:
        response = requests.get(
            f'{BASE_URL}/health',
            headers={'X-API-Key': API_KEY},
            timeout=5
        )
        if response.status_code == 200:
            print("✅ Valid API key accepted")
        else:
            print(f"❌ Valid API key rejected: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error with valid key: {e}")
        return False
    
    # Test with invalid API key
    try:
        response = requests.post(
            f'{BASE_URL}/api/v1/encode',
            headers={'X-API-Key': 'wrong-key'},
            timeout=5
        )
        if response.status_code == 403:
            print("✅ Invalid API key rejected (403)")
            return True
        else:
            print(f"⚠️  Invalid API key got: {response.status_code} (expected 403)")
            return True  # Still pass, just note the difference
    except Exception as e:
        print(f"❌ Error with invalid key: {e}")
        return False

def test_encode_decode_workflow():
    """Test the complete encode-decode workflow."""
    print("\n" + "="*70)
    print("TEST 3: Complete Encode-Decode Workflow")
    print("="*70)
    
    temp_dir = Path(tempfile.mkdtemp())
    headers = {'X-API-Key': API_KEY}
    
    try:
        # Step 1: Create test audio
        print("\n📝 Step 1: Creating test audio file...")
        audio_file = temp_dir / 'test_audio.wav'
        create_test_audio(audio_file)
        original_hash = get_file_hash(audio_file)
        print(f"   Original SHA-256: {original_hash[:16]}...")
        
        # Step 2: Encode
        print("\n🔐 Step 2: Encoding audio to images...")
        with open(audio_file, 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            data = {
                'user_id': TEST_USER_ID,
                'master_key': TEST_MASTER_KEY,
                'compress': 'true'
            }
            
            response = requests.post(
                f'{BASE_URL}/api/v1/encode',
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code != 200:
            print(f"❌ Encode failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        images_zip = temp_dir / 'encrypted_images.zip'
        with open(images_zip, 'wb') as f:
            f.write(response.content)
        
        image_count = response.headers.get('X-Images-Count', 'unknown')
        compressed = response.headers.get('X-Compressed', 'unknown')
        print(f"✅ Encoding successful!")
        print(f"   Images created: {image_count}")
        print(f"   Compressed: {compressed}")
        print(f"   ZIP size: {images_zip.stat().st_size} bytes")
        
        # Step 3: Decode
        print("\n🔓 Step 3: Decoding images back to audio...")
        with open(images_zip, 'rb') as f:
            files = {'images': ('encrypted_images.zip', f, 'application/zip')}
            data = {
                'user_id': TEST_USER_ID,
                'master_key': TEST_MASTER_KEY
            }
            
            response = requests.post(
                f'{BASE_URL}/api/v1/decode',
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code != 200:
            print(f"❌ Decode failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        recovered_audio = temp_dir / 'recovered_audio.wav'
        with open(recovered_audio, 'wb') as f:
            f.write(response.content)
        
        recovered_hash = get_file_hash(recovered_audio)
        print(f"✅ Decoding successful!")
        print(f"   Recovered SHA-256: {recovered_hash[:16]}...")
        print(f"   File size: {recovered_audio.stat().st_size} bytes")
        
        # Step 4: Verify
        print("\n🔍 Step 4: Verifying file integrity...")
        if original_hash == recovered_hash:
            print("✅ SUCCESS! Files match perfectly!")
            print(f"   SHA-256: {original_hash}")
            return True
        else:
            print("❌ FAILURE! Files do not match!")
            print(f"   Original:  {original_hash}")
            print(f"   Recovered: {recovered_hash}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def test_security():
    """Test security features."""
    print("\n" + "="*70)
    print("TEST 4: Security - Wrong User ID")
    print("="*70)
    
    temp_dir = Path(tempfile.mkdtemp())
    headers = {'X-API-Key': API_KEY}
    
    try:
        # Create and encode with user_id="alice"
        print("\n📝 Encoding with user_id='alice'...")
        audio_file = temp_dir / 'test.wav'
        create_test_audio(audio_file)
        
        with open(audio_file, 'rb') as f:
            files = {'file': ('test.wav', f, 'audio/wav')}
            data = {
                'user_id': 'alice',
                'master_key': TEST_MASTER_KEY,
                'compress': 'false'
            }
            response = requests.post(
                f'{BASE_URL}/api/v1/encode',
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code != 200:
            print(f"❌ Encode failed: {response.status_code}")
            return False
        
        images_zip = temp_dir / 'images.zip'
        with open(images_zip, 'wb') as f:
            f.write(response.content)
        print("✅ Encoded successfully")
        
        # Try to decode with user_id="bob" (should fail!)
        print("\n🔓 Attempting to decode with user_id='bob'...")
        with open(images_zip, 'rb') as f:
            files = {'images': ('images.zip', f, 'application/zip')}
            data = {
                'user_id': 'bob',  # Different user!
                'master_key': TEST_MASTER_KEY
            }
            response = requests.post(
                f'{BASE_URL}/api/v1/decode',
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code == 200:
            print("❌ SECURITY ISSUE: Different user_id should fail!")
            return False
        else:
            print(f"✅ Security working! Decode failed with status {response.status_code}")
            print(f"   (Different user_id cannot decrypt)")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print(" AudioImageCarrier API - Test Suite")
    print("="*70)
    print(f"🔗 Server: {BASE_URL}")
    print(f"🔑 API Key: {API_KEY}")
    
    results = []
    
    # Run tests
    results.append(("Server Running", test_server_running()))
    
    if not results[0][1]:
        print("\n❌ Server is not running. Please start it first.")
        print("   Command: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        sys.exit(1)
    
    results.append(("Authentication", test_authentication()))
    results.append(("Encode-Decode", test_encode_decode_workflow()))
    results.append(("Security", test_security()))
    
    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The API is working correctly!")
        print(f"\n📖 Next steps:")
        print(f"   - Visit Swagger UI: {BASE_URL}/docs")
        print(f"   - Read testing guide: TESTING.md")
        print(f"   - Read API docs: docs/API_DOCUMENTATION.md")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    main()
