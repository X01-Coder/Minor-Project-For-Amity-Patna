"""
Decode a single PNG image back to audio
"""
import sys
sys.path.insert(0, r'E:\Projects\minnor Project\New_backend\AudioImageCarrier-Backend\scripts')

from pathlib import Path
from audio_image_chunked import decode_images_to_file

# Configuration
IMAGE_PATH = r"E:\Projects\minnor Project\New_backend\AudioImageCarrier-Backend\output\upload_fd51a019_Recording_part0001_of_0001.png"
OUTPUT_DIR = Path(__file__).parent / "output"
USER_ID = 'prince'
MASTER_KEY = 'a7f3e9d2c1b4568790fedcba0123456789abcdef0123456789abcdef01234567'

def decode_single_image():
    """Decode a single PNG image to audio."""
    print("="*70)
    print("🔓 Decoding PNG Image to Audio")
    print("="*70)
    
    image_path = Path(IMAGE_PATH)
    
    # Check if file exists
    if not image_path.exists():
        print(f"\n❌ Error: Image not found at: {IMAGE_PATH}")
        return False
    
    file_size_mb = image_path.stat().st_size / (1024 * 1024)
    print(f"\n📁 Input Image:")
    print(f"   Path: {image_path}")
    print(f"   Size: {file_size_mb:.2f} MB")
    print(f"   Format: {image_path.suffix}")
    
    # Output path
    output_audio = OUTPUT_DIR / "decoded_from_single_image.m4a"
    
    # The decode function expects a directory, so we use the parent directory
    image_dir = image_path.parent
    
    print(f"\n🔓 Decoding with:")
    print(f"   User ID: {USER_ID}")
    print(f"   Master Key: {MASTER_KEY[:16]}...{MASTER_KEY[-16:]}")
    print(f"   Image directory: {image_dir}")
    
    try:
        # Decode using the script directly
        # The function reads all PNG images from the directory
        decode_images_to_file(
            indir=image_dir,
            out_file=output_audio,
            user_id=USER_ID,
            master_hex=MASTER_KEY
        )
        
        if output_audio.exists():
            output_size_mb = output_audio.stat().st_size / (1024 * 1024)
            print(f"\n✅ Decoding Successful!")
            print(f"\n📦 Output:")
            print(f"   File: {output_audio}")
            print(f"   Size: {output_size_mb:.2f} MB")
            print(f"\n🎵 You can now play: {output_audio}")
            return True
        else:
            print(f"\n❌ Error: Output file was not created")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during decoding: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    decode_single_image()
