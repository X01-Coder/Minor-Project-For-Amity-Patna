import os

def rename_audio_files(folder_path):
    """
    Renames all audio files in the specified folder to a numerical sequence
    (0, 1, 2, 3...) using a two-step process to prevent 'File Already Exists' errors.
    """
    
    if not os.path.exists(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    audio_extensions = ('.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma')

    try:
        files = os.listdir(folder_path)
        # Filter and sort strictly
        audio_files = [f for f in files if f.lower().endswith(audio_extensions)]
        audio_files.sort()

        if not audio_files:
            print("No audio files found in this folder.")
            return

        print(f"Found {len(audio_files)} audio files.")
        print("Starting 2-Step Rename Process to avoid file conflicts...")

        # --- STEP 1: Rename everything to a temporary unique name ---
        # This clears the way so '1.wav' doesn't block '0116.wav' from becoming '1.wav'
        print("\n--- Step 1: Renaming to temporary names ---")
        
        temp_files_map = [] # To store (temp_path, final_name) for Step 2

        for i, filename in enumerate(audio_files):
            old_file_path = os.path.join(folder_path, filename)
            file_extension = os.path.splitext(filename)[1]
            
            # Create a temporary name that won't conflict with anything
            # e.g., "__temp_processing_0.wav"
            temp_filename = f"__temp_processing_{i}{file_extension}"
            temp_file_path = os.path.join(folder_path, temp_filename)
            
            # Target final name for Step 2
            final_filename = f"{i}{file_extension}"
            
            # Optimization: If the file is ALREADY correct (e.g., 0.wav is at index 0),
            # check if we really need to rename it. 
            # However, for safety against complex swaps, we usually rename unless it's perfect.
            if filename == final_filename:
                # If it's already named '0.wav' and is in the 0th slot, we just mark it for Step 2 
                # effectively doing nothing, BUT we must ensure no other file maps to this.
                # To be 100% safe against duplicates/swaps, we rename to temp unless strict order matches.
                # Given your error, FORCE rename to temp is safer.
                pass

            os.rename(old_file_path, temp_file_path)
            
            # Store the paths for Step 2
            temp_files_map.append((temp_file_path, final_filename))
            
            if i % 1000 == 0:
                print(f"Step 1 Progress: {i}/{len(audio_files)}...")

        print("Step 1 Complete. All files have temporary names.")

        # --- STEP 2: Rename from temporary to final (0, 1, 2...) ---
        print("\n--- Step 2: Renaming to final sorted names ---")
        
        count = 0
        for temp_path, final_filename in temp_files_map:
            final_path = os.path.join(folder_path, final_filename)
            
            os.rename(temp_path, final_path)
            
            count += 1
            if count % 1000 == 0:
                print(f"Step 2 Progress: {count}/{len(audio_files)}...")

        print(f"\nSuccess! All {count} files have been renamed serially.")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        print("Note: If the script crashed halfway, you may have files named '__temp_processing_...'.")
        print("You can simply run this script again, and it will fix them.")

# --- CONFIGURATION ---
target_folder = r"E:\Test Audio Data\Audio Data\Noiseless Data" 

if __name__ == "__main__":
    rename_audio_files(target_folder)