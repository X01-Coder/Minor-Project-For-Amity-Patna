import os
import random
import urllib.request
import ssl
from pydub import AudioSegment
from pydub.generators import WhiteNoise

# --- CONFIGURATION ---
clean_folder = r"E:\Test Audio Data\Audio Data\Noiseless Data"
output_folder = r"E:\Test Audio Data\Audio Data\Noisy Data"
noise_storage_folder = r"E:\Test Audio Data\Noise_Samples"

# --- GENERATE 100+ NOISE SOURCES ---
# Instead of hardcoding 100+ lines, we programmatically generate links 
# for 21 categories x 5 samples each = 105 noise files from the MS-SNSD dataset.
base_url = "https://raw.githubusercontent.com/microsoft/MS-SNSD/master/noise_test/"

categories = [
    "AirConditioner", "Airport", "Babble", "Bus", "Cafe", "Car", 
    "CopyMachine", "Field", "Kitchen", "Munching", "Neighbour", 
    "Office", "Park", "PassengerTrain", "Restaurant", "School", 
    "Station", "Traffic", "Typing", "VacuumCleaner", "WasherDryer"
]

noise_sources = []
for category in categories:
    # We grab files numbered 1 to 5 for each category
    for i in range(1, 6):
        filename = f"{category}_{i}.wav"
        url = f"{base_url}{filename}"
        # Tuple format: (Display Name, Local Filename, URL)
        noise_sources.append((f"{category} {i}", filename, url))

# Volume adjustment (dB). -10 makes noise quieter than the voice.
noise_volume_db = -10 

def download_noise_files():
    """Downloads all noise files defined in noise_sources."""
    if not os.path.exists(noise_storage_folder):
        os.makedirs(noise_storage_folder)

    downloaded_paths = []
    
    # Create an unverified SSL context to avoid certificate errors
    ssl_context = ssl._create_unverified_context()

    print(f"--- Checking {len(noise_sources)} Noise Files ---")
    
    # We will try to download all, but continue if some are missing (404)
    for index, (name, filename, url) in enumerate(noise_sources):
        save_path = os.path.join(noise_storage_folder, filename)
        
        if not os.path.exists(save_path):
            # Print less verbose output for 100 files, just status updates
            if index % 10 == 0: 
                print(f"Checking file {index+1}/{len(noise_sources)}...")
                
            try:
                # Add a user-agent to avoid 403 Forbidden errors
                req = urllib.request.Request(
                    url, 
                    data=None, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, context=ssl_context) as response, open(save_path, 'wb') as out_file:
                    out_file.write(response.read())
                # Only add to valid list if download succeeded
                downloaded_paths.append(save_path)
            except Exception as e:
                # It's normal for some specific numbers to be missing in the dataset
                # We just skip them without stopping the script
                pass 
        else:
            downloaded_paths.append(save_path)
    
    print(f"\nTotal valid noise files available: {len(downloaded_paths)}")
    return downloaded_paths

def generate_fallback_noise(duration_ms=5000):
    """Generates synthetic white noise if downloads fail."""
    print("Generating synthetic White Noise (Fallback)...")
    noise = WhiteNoise().to_audio_segment(duration=duration_ms)
    return noise

def create_noisy_dataset():
    # 1. Prepare Folders
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 2. Get Noise Files
    valid_noise_paths = download_noise_files()
    
    loaded_noises = []

    # 3. Load Noises into RAM
    if valid_noise_paths:
        print("\nLoading noise audio into memory (this may take a moment for 100+ files)...")
        for path in valid_noise_paths:
            try:
                audio = AudioSegment.from_file(path)
                audio = audio + noise_volume_db
                loaded_noises.append(audio)
            except Exception as e:
                print(f"Could not load audio {path}: {e}")
    
    # --- FALLBACK MECHANISM ---
    if not loaded_noises:
        print("\nWARNING: No noise files could be downloaded.")
        print("Switching to SYNTHETIC WHITE NOISE so the process can continue.")
        # Generate a 10-second chunk of white noise
        fallback_noise = generate_fallback_noise(10000) + noise_volume_db
        loaded_noises.append(fallback_noise)

    # 4. Process Clean Files
    supported_extensions = ('.wav', '.mp3', '.flac', '.ogg')
    files = [f for f in os.listdir(clean_folder) if f.lower().endswith(supported_extensions)]
    
    total_files = len(files)
    print(f"\nFound {total_files} clean files. Applying random noises...")

    for i, filename in enumerate(files):
        try:
            clean_file_path = os.path.join(clean_folder, filename)
            save_path = os.path.join(output_folder, filename)
            
            clean_audio = AudioSegment.from_file(clean_file_path)
            clean_duration = len(clean_audio)

            # --- Randomly Select One Noise Type ---
            selected_noise_audio = random.choice(loaded_noises)
            
            # --- Prepare the Noise Segment ---
            noise_duration = len(selected_noise_audio)
            
            if noise_duration > clean_duration:
                # Pick random start point
                max_start = noise_duration - clean_duration
                start_point = random.randint(0, max_start)
                noise_segment = selected_noise_audio[start_point : start_point + clean_duration]
            else:
                # Loop noise if it's too short
                noise_segment = selected_noise_audio * (int(clean_duration / noise_duration) + 1)
                noise_segment = noise_segment[:clean_duration]

            # --- Overlay ---
            noisy_audio = clean_audio.overlay(noise_segment)

            # --- Export ---
            ext = os.path.splitext(filename)[1].replace('.', '')
            noisy_audio.export(save_path, format=ext)

            if i % 100 == 0:
                print(f"Processed {i}/{total_files}: {filename}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print("\nAll done! Random noises applied.")

if __name__ == "__main__":
    create_noisy_dataset()